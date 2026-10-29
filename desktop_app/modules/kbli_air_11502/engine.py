import os
import re
import time
import random
import threading
import queue
import openpyxl
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config import CDP_URL
from core.logger import logger
from core.event_bus import EngineState
from core.audit_logger import audit_logger
from core.window_controller import WindowController
from core.browser_manager import BrowserManager
from modules.kbli_air_11502.validator import ExcelKBLIAir11502Validator
from modules.kbli_air_11502.selectors import KBLI_AIR_11502_SELECTORS

# ==============================================================================
# HELPER BEHAVIOR MANUSIA & PLAYWRIGHT
# ==============================================================================

def responsive_sleep(min_sec=1.0, max_sec=2.0, event_bus=None, allow_hesitation=True):
    duration = random.uniform(min_sec, max_sec)
    if allow_hesitation and random.random() < 0.2:
        duration += random.uniform(1.0, 2.0)
    end_time = time.time() + duration
    while time.time() < end_time:
        if event_bus and event_bus.is_stop_requested():
            return False
        if event_bus and event_bus.is_paused():
            event_bus.wait_if_paused()
            if event_bus.is_stop_requested():
                return False
        time.sleep(min(0.08, max(0.01, end_time - time.time())))
    return True

def human_jitter(min_sec=0.1, max_sec=0.25, event_bus=None):
    responsive_sleep(min_sec, max_sec, event_bus=event_bus, allow_hesitation=False)

def random_sleep(min_sec=1.0, max_sec=2.0, event_bus=None, allow_hesitation=True):
    responsive_sleep(min_sec, max_sec, event_bus=event_bus, allow_hesitation=allow_hesitation)

def safe_click(page, selector_or_locator, timeout=20000, event_bus=None, force=False):
    human_jitter(0.1, 0.2, event_bus=event_bus)
    if isinstance(selector_or_locator, str):
        loc = page.locator(selector_or_locator).first
    else:
        loc = selector_or_locator
    loc.wait_for(state="attached", timeout=timeout)
    try:
        loc.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    human_jitter(0.1, 0.2, event_bus=event_bus)
    try:
        loc.click(timeout=timeout, force=force)
    except Exception as e:
        err_msg = str(e).lower()
        if "intercepts pointer events" in err_msg or "subtree intercepts" in err_msg or not force:
            logger.bot("Intersepsi klik terdeteksi. Mengulang klik dengan force=True...")
            human_jitter(0.1, 0.2, event_bus=event_bus)
            loc.click(timeout=8000, force=True)
        else:
            raise e

def normalize_text(text):
    """Normalisasi string: lowercase, hilangkan non-breaking space, collapse whitespace."""
    if text is None:
        return ""
    t = str(text).replace("\xa0", " ").strip().lower()
    return re.sub(r"\s+", " ", t)

def add_remarks_to_element(page, container_selector, note_text, event_bus=None, worker_prefix=""):
    """Membuka modal Catatan pada elemen container, mengetik catatan, klik simpan, lalu tutup modal."""
    container = page.locator(container_selector).first
    container.wait_for(state="attached", timeout=30000)
    try:
        container.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    random_sleep(0.4, 0.7, event_bus=event_bus)

    # Cari tombol Catatan yang VISIBLE di dalam container
    btn_catatan = container.locator("button[title='Catatan']:visible, button[aria-label='Catatan']:visible").first
    if btn_catatan.count() == 0 or not btn_catatan.is_visible():
        all_btns = container.locator("button[title='Catatan'], button[aria-label='Catatan']")
        btn_catatan = None
        for i in range(all_btns.count()):
            b = all_btns.nth(i)
            if b.is_visible():
                btn_catatan = b
                break

    if not btn_catatan:
        raise Exception(f"Tombol Catatan visible tidak ditemukan pada container {container_selector}")

    safe_click(page, btn_catatan, timeout=20000, event_bus=event_bus)
    random_sleep(0.7, 1.1, event_bus=event_bus)

    dialog = page.locator("div[role='dialog']").first
    try:
        dialog.wait_for(state="visible", timeout=25000)
    except PlaywrightTimeoutError:
        raise Exception("Modal pop-up Catatan tidak muncul setelah tombol Catatan diklik")

    note_str = str(note_text).strip()

    # Cek apakah catatan sudah pernah tercatat sebelumnya di riwayat pesan
    already_exists = False
    try:
        bubbles = dialog.locator("div[class*='whitespace-pre-wrap'], div[class*='wrap-break-word']")
        for i in range(bubbles.count()):
            if bubbles.nth(i).inner_text().strip() == note_str:
                already_exists = True
                break
    except Exception:
        pass

    if already_exists:
        logger.info(f"{worker_prefix}Catatan '{note_str}' sudah tercatat sebelumnya. Melewati pengiriman ulang.")
    else:
        textarea = dialog.locator("textarea[placeholder*='Tambah catatan'], textarea").first
        try:
            textarea.wait_for(state="visible", timeout=25000)
        except PlaywrightTimeoutError:
            raise Exception("Textarea Catatan tidak ditemukan di dalam dialog")

        textarea.click()
        human_jitter(0.1, 0.2, event_bus=event_bus)
        textarea.fill(note_str)
        human_jitter(0.15, 0.25, event_bus=event_bus)

        btn_simpan = dialog.locator("button[title='Simpan']").first
        btn_simpan.wait_for(state="visible", timeout=25000)
        safe_click(page, btn_simpan, timeout=20000, event_bus=event_bus)
        random_sleep(0.8, 1.2, event_bus=event_bus)

    try:
        btn_close = dialog.locator("button[aria-label='Dismiss'], button[title='Tutup'], button:has-text('Tutup')").first
        if btn_close.is_visible(timeout=4000):
            safe_click(page, btn_close, timeout=8000, event_bus=event_bus)
        else:
            page.keyboard.press("Escape")
    except Exception:
        page.keyboard.press("Escape")

    try:
        dialog.wait_for(state="hidden", timeout=8000)
    except Exception:
        page.keyboard.press("Escape")

    random_sleep(0.4, 0.7, event_bus=event_bus)

def _add_remarks_to_master_kbli_if_visible(page, note_text, master_selector, event_bus=None, worker_prefix=""):
    """
    Memeriksa apakah rincian Master KBLI (div[id^='kbli#'], div[id='kbli']) ada dan terlihat di form.
    Jika ada dan visible: buka modal catatan, isi catatan (#0 atau #4), simpan, dan tutup.
    Jika tidak ada atau tersembunyi: lewati secara aman tanpa error.
    """
    if event_bus and event_bus.is_stop_requested():
        return False
    try:
        master_container = page.locator(master_selector).first
        if master_container.count() > 0 and master_container.is_visible():
            logger.bot(f"{worker_prefix}Rincian Master KBLI terdeteksi aktif. Memberikan Catatan '{note_text}' pada rincian kbli...")
            add_remarks_to_element(page, master_selector, note_text, event_bus=event_bus, worker_prefix=worker_prefix)
            return True
        else:
            return False
    except Exception as e:
        logger.warning(f"⚠️ {worker_prefix}Peringatan saat memberikan catatan pada Master KBLI: {e}")
        return False

def _ensure_blok2_and_usaha_menu_expanded(page, event_bus=None, worker_prefix=""):
    """
    Memastikan menu Blok II dan sub-menu 'Keterangan Usaha/Perusahaan' di sidebar
    dalam kondisi terbuka (expanded).
    """
    blok2_elem = page.locator(KBLI_AIR_11502_SELECTORS["sidebar_blok_ii"]).first
    try:
        blok2_elem.wait_for(state="attached", timeout=20000)
    except Exception:
        return False, "Menu Blok II tidak ditemukan di sidebar"

    try:
        blok2_elem.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass

    # Cek apakah collapsible Blok II sudah terbuka
    blok2_collapsible = page.locator(
        "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='SE2026 - L BLOK II' or contains(., 'BLOK II')]"
        "/following-sibling::div[starts-with(@id, 'collapsible-')] | "
        "//div[contains(@class, 'fasih-form-sidebar')]//*[@title='SE2026 - L BLOK II' or contains(., 'BLOK II')]"
        "/ancestor::div[contains(@class, 'fasih-form-sidebar')][1]/following-sibling::div[starts-with(@id, 'collapsible-')]"
    ).first
    if blok2_collapsible.count() == 0 or blok2_collapsible.get_attribute("data-expanded") is None:
        logger.bot(f"{worker_prefix}Membuka menu Blok II di sidebar...")
        safe_click(page, blok2_elem, timeout=15000, event_bus=event_bus)
        random_sleep(0.7, 1.2, event_bus=event_bus)

    # Cek sub-header 'Keterangan Usaha/Perusahaan'
    ket_usaha = page.locator(KBLI_AIR_11502_SELECTORS["sidebar_keterangan_usaha"]).first
    if ket_usaha.count() > 0:
        ket_collapsible = page.locator(
            "xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[@title='Keterangan Usaha/Perusahaan' or text()='Keterangan Usaha/Perusahaan']"
            "/following-sibling::div[starts-with(@id, 'collapsible-')] | "
            "//div[contains(@class, 'fasih-form-sidebar')]//div[@title='Keterangan Usaha/Perusahaan' or text()='Keterangan Usaha/Perusahaan']"
            "/ancestor::div[contains(@class, 'fasih-form-sidebar')][1]/following-sibling::div[starts-with(@id, 'collapsible-')]"
        ).first
        if ket_collapsible.count() > 0 and ket_collapsible.get_attribute("data-expanded") is None:
            logger.bot(f"{worker_prefix}Membuka sub-menu 'Keterangan Usaha/Perusahaan'...")
            safe_click(page, ket_usaha, timeout=10000, event_bus=event_bus)
            random_sleep(0.6, 1.0, event_bus=event_bus)

    return True, None

def _get_valid_usaha_items(page):
    """Mengambil daftar elemen dan nama usaha yang valid di sub-menu Keterangan Usaha."""
    raw_items = page.locator(KBLI_AIR_11502_SELECTORS["sidebar_sub_usaha_items"]).all()
    valid = []
    for item in raw_items:
        try:
            t = (item.get_attribute("title") or item.inner_text() or "").strip()
            t_upper = t.upper()
            if t and not any(skip in t_upper for skip in ["BLOK II", "KETERANGAN USAHA/PERUSAHAAN", "CATATAN"]):
                valid.append((item, t))
        except Exception:
            pass
    return valid

def _find_and_open_matching_business(page, excel_keg_utama, event_bus=None, worker_prefix="", check_stop_fn=None):
    """
    Menemukan dan membuka rincian usaha yang sesuai dengan kegiatan utama (keg_utama) di Excel:
    1. Membuka sidebar Blok II dan sub-menu Keterangan Usaha/Perusahaan.
    2. Mendeteksi seluruh usaha yang terdaftar di Blok II.
    3. Jika jumlah usaha == 0 -> return False, None, 'Tidak ada rincian usaha di Blok II'.
    4. Jika jumlah usaha >= 1:
       - Loop setiap usaha satu per satu:
         - Pastikan sidebar terbuka, lalu klik item usaha ke-i.
         - Periksa isian field_kegiatan_utama pada form rincian usaha vs excel_keg_utama.
         - Jika cocok: return True, matched_nama_usaha, None.
         - Jika tidak cocok: lanjut periksa usaha berikutnya.
    5. Jika seluruh usaha telah diperiksa dan tidak ada yang cocok:
       - return False, None, pesan keterangan tidak cocok.
    """
    logger.bot(f"{worker_prefix}Membuka menu Blok II di sidebar...")
    ok_menu, err_menu = _ensure_blok2_and_usaha_menu_expanded(page, event_bus=event_bus, worker_prefix=worker_prefix)
    if not ok_menu:
        return False, None, err_menu

    # Ambil daftar usaha valid
    valid_items = _get_valid_usaha_items(page)
    count = len(valid_items)

    if count == 0:
        random_sleep(0.8, 1.2, event_bus=event_bus)
        valid_items = _get_valid_usaha_items(page)
        count = len(valid_items)

    if count == 0:
        return False, None, "Tidak ada rincian usaha di Blok II"

    usaha_names = [name for _, name in valid_items]

    if count == 1:
        logger.bot(f"{worker_prefix}Ditemukan 1 usaha: '{usaha_names[0]}'. Memeriksa kesesuaian kegiatan utama...")
    else:
        logger.bot(f"{worker_prefix}Ditemukan {count} usaha di Blok II. Mencari usaha yang sesuai dengan kegiatan utama '{excel_keg_utama[:35]}'...")

    last_web_val = ""

    for idx in range(count):
        if check_stop_fn and not check_stop_fn():
            return False, None, "Dihentikan oleh pengguna saat pencarian usaha"
        if event_bus and event_bus.is_stop_requested():
            return False, None, "Dihentikan oleh pengguna"

        curr_name = usaha_names[idx] if idx < len(usaha_names) else f"Usaha #{idx+1}"

        if count > 1:
            logger.bot(f"{worker_prefix}[Usaha {idx+1}/{count}: '{curr_name}'] Membuka halaman rincian usaha...")

        # Pastikan menu Blok II & Keterangan Usaha tetap expanded
        _ensure_blok2_and_usaha_menu_expanded(page, event_bus=event_bus, worker_prefix=worker_prefix)

        # Re-query elemen untuk menghindari stale handle
        current_items = _get_valid_usaha_items(page)
        if idx >= len(current_items):
            logger.warning(f"⚠️ {worker_prefix}Item usaha ke-{idx+1} tidak ditemukan di sub-sidebar, mencoba lanjutkan...")
            continue

        item_loc, _ = current_items[idx]
        safe_click(page, item_loc, timeout=15000, event_bus=event_bus)
        random_sleep(1.2, 1.8, event_bus=event_bus)

        # Validasi keg_utama pada formulir usaha yang sedang aktif
        keg_cocok, keg_web = _validate_kegiatan_utama(page, excel_keg_utama, timeout=15000)
        last_web_val = keg_web

        if keg_cocok:
            if count > 1:
                logger.success(f"{worker_prefix}[Usaha {idx+1}/{count}: '{curr_name}'] Kegiatan utama COCOK! ('{keg_web[:35]}')")
            else:
                logger.success(f"{worker_prefix}Kegiatan utama cocok: '{keg_web[:35]}'")
            return True, curr_name, None
        else:
            if count > 1:
                logger.info(f"{worker_prefix}[Usaha {idx+1}/{count}: '{curr_name}'] Tidak cocok (Web: '{keg_web[:25]}' vs Excel: '{excel_keg_utama[:25]}').")

    # Jika setelah memeriksa semua usaha tidak ada yang cocok
    if count == 1:
        return False, usaha_names[0], f"Kegiatan utama tidak sesuai (Excel: '{excel_keg_utama[:25]}' vs Web: '{last_web_val[:25]}')"
    else:
        return False, None, f"Dari {count} usaha di Blok II, tidak ada yang cocok dengan kegiatan utama '{excel_keg_utama[:25]}'"

def _validate_kegiatan_utama(page, excel_keg, timeout=20000):
    """
    Memeriksa isian kegiatan utama di web form eform fasih vs excel.
    Perbandingan case-insensitive dan spasi dinormalisasi.
    """
    keg_loc = page.locator(KBLI_AIR_11502_SELECTORS["field_kegiatan_utama"]).first
    keg_loc.wait_for(state="attached", timeout=timeout)
    try:
        keg_loc.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass

    web_val = ""
    try:
        web_val = keg_loc.input_value().strip()
    except Exception:
        pass
    if not web_val:
        web_val = (keg_loc.get_attribute("value") or keg_loc.inner_text() or "").strip()

    is_match = (normalize_text(excel_keg) == normalize_text(web_val))
    return is_match, web_val

def _clean_kbli_code(val):
    """Membersihkan nilai kode KBLI (menghilangkan trailing .0 jika terbaca sebagai float openpyxl)."""
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.strip()

def _fill_master_kbli(page, kbli_baru, event_bus=None, worker_prefix=""):
    """
    Mengisi atau mengganti kode KBLI pada komponen Master KBLI (div[id^='kbli#']).
    Setelah mengetikkan kode KBLI:
    1. Menunggu popover loading pencarian KBLI selesai ('Memuat opsi...')
    2. Menunggu popover pilihan opsi KBLI muncul
    3. Mengklik opsi KBLI yang dimaksud (berdasarkan data-key / kode KBLI)
    4. Memverifikasi opsi terpilih sebelum lanjut ke step berikutnya
    """
    kbli_box = page.locator(KBLI_AIR_11502_SELECTORS["container_master_kbli"]).first
    kbli_box.wait_for(state="visible", timeout=20000)
    try:
        kbli_box.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    random_sleep(0.4, 0.7, event_bus=event_bus)

    kbli_clean = _clean_kbli_code(kbli_baru)
    if not kbli_clean:
        raise Exception("Nilai KBLI_Terbaru di Excel kosong")

    # 1. Input/textarea master KBLI
    target_input = kbli_box.locator(KBLI_AIR_11502_SELECTORS["textarea_master_kbli"]).first
    target_input.wait_for(state="visible", timeout=10000)
    safe_click(page, target_input, timeout=8000, event_bus=event_bus)
    human_jitter(0.1, 0.2, event_bus=event_bus)

    # 2. Ketikkan KBLI Terbaru (langsung menimpa isian lama tanpa klik reset)
    logger.bot(f"{worker_prefix}Mengetikkan KBLI Terbaru '{kbli_clean}'...")
    target_input.click()
    try:
        target_input.select_text(timeout=2000)
    except Exception:
        page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    target_input.press_sequentially(kbli_clean, delay=50)
    human_jitter(0.2, 0.3, event_bus=event_bus)

    # 3. Tunggu popover loading search KBLI ('Memuat opsi...')
    logger.bot(f"{worker_prefix}Menunggu pencarian Master KBLI untuk '{kbli_clean}'...")
    loading_selector = (
        "div[role='dialog']:has-text('Memuat opsi...'), "
        "div:has-text('Memuat opsi...'), "
        "span:has-text('Memuat opsi...')"
    )
    loading_elem = page.locator(loading_selector).first

    # Beri toleransi waktu untuk mendeteksi apakah popover loading muncul
    try:
        if loading_elem.is_visible(timeout=2500):
            logger.bot(f"{worker_prefix}Pop-over loading terdeteksi ('Memuat opsi...'), menunggu selesai...")
            loading_elem.wait_for(state="hidden", timeout=20000)
            logger.bot(f"{worker_prefix}Pop-over loading selesai.")
    except Exception:
        pass

    # 4. Tunggu popover pilihan KBLI muncul sesuai kode KBLI
    option_selector = (
        f"li[role='option'][data-key='{kbli_clean}'], "
        f"[role='option'][data-key='{kbli_clean}'], "
        f"li[role='option']:has-text('{kbli_clean}'), "
        f"div[role='option']:has-text('{kbli_clean}'), "
        f"[role='listbox'] [role='option']:has-text('{kbli_clean}')"
    )
    option_elem = page.locator(option_selector).first

    try:
        option_elem.wait_for(state="visible", timeout=15000)
    except Exception:
        # Jika popover belum muncul, coba tekan ArrowDown sekali untuk memicu dropdown
        logger.bot(f"{worker_prefix}Opsi belum langsung muncul, mencoba menekan ArrowDown...")
        page.keyboard.press("ArrowDown")
        random_sleep(0.5, 0.8, event_bus=event_bus)
        option_elem.wait_for(state="visible", timeout=8000)

    # Dapatkan teks rincian KBLI yang muncul untuk logging
    opt_text = ""
    try:
        opt_text = option_elem.inner_text().splitlines()[0].strip()
    except Exception:
        opt_text = kbli_clean

    logger.bot(f"{worker_prefix}Ditemukan opsi KBLI: '{opt_text}'. Mengeklik opsi...")
    safe_click(page, option_elem, timeout=10000, event_bus=event_bus)
    random_sleep(0.8, 1.4, event_bus=event_bus)

    # 6. Verifikasi dan log
    logger.bot(f"{worker_prefix}KBLI Terbaru '[{kbli_clean}]' berhasil dipilih.")
    random_sleep(0.5, 0.8, event_bus=event_bus)

def _select_master_kbli_radio(page, kbli_genai, event_bus=None, worker_prefix=""):
    """
    Memilih opsi radio 'Pilih dari Master KBLI' (value 999999) pada rincian kbli_genai,
    dan memverifikasi sampai benar-benar aktif/terpilih melalui multi-stage fallback.
    """
    master_input = kbli_genai.locator("input[value='999999']").first
    master_label = kbli_genai.locator("label:has-text('Pilih dari Master KBLI')").first
    master_control = kbli_genai.locator(
        "div[role='radio']:has(+ label:has-text('Pilih dari Master KBLI')), "
        "div[role='group']:has(input[value='999999']) div[role='radio']"
    ).first
    parent_group = kbli_genai.locator("div[role='group']:has(input[value='999999'])").first

    def _is_active():
        try:
            if master_input.count() > 0:
                if master_input.is_checked() or master_input.get_attribute("data-checked") is not None:
                    return True
            if parent_group.count() > 0 and parent_group.get_attribute("data-checked") is not None:
                return True
            if master_control.count() > 0 and master_control.get_attribute("data-checked") is not None:
                return True
        except Exception:
            pass
        return False

    if _is_active():
        logger.bot(f"{worker_prefix}Opsi 'Pilih dari Master KBLI' sudah aktif.")
        return True

    # 1. Pastikan area kbli_genai terlihat di layar
    try:
        master_label.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        try:
            kbli_genai.scroll_into_view_if_needed(timeout=5000)
        except Exception:
            pass

    random_sleep(0.3, 0.6, event_bus=event_bus)

    # Metode 1: Klik label 'Pilih dari Master KBLI' secara normal
    try:
        if master_label.count() > 0 and master_label.is_visible():
            logger.bot(f"{worker_prefix}Mengeklik label 'Pilih dari Master KBLI'...")
            master_label.click(timeout=6000)
            random_sleep(0.6, 1.0, event_bus=event_bus)
    except Exception as e:
        logger.warning(f"{worker_prefix}Klik label gagal: {e}")

    if _is_active():
        logger.bot(f"{worker_prefix}Opsi 'Pilih dari Master KBLI' berhasil dipilih (via label).")
        return True

    # Metode 2: Klik div role='radio' (lingkaran radio button)
    try:
        if master_control.count() > 0 and master_control.is_visible():
            logger.bot(f"{worker_prefix}Mengeklik radio control 'Pilih dari Master KBLI'...")
            master_control.click(timeout=6000)
            random_sleep(0.6, 1.0, event_bus=event_bus)
    except Exception as e:
        logger.warning(f"{worker_prefix}Klik control radio gagal: {e}")

    if _is_active():
        logger.bot(f"{worker_prefix}Opsi 'Pilih dari Master KBLI' berhasil dipilih (via control).")
        return True

    # Metode 3: Klik pembungkus role='group'
    try:
        if parent_group.count() > 0 and parent_group.is_visible():
            logger.bot(f"{worker_prefix}Mengeklik group 'Pilih dari Master KBLI'...")
            parent_group.click(timeout=6000)
            random_sleep(0.6, 1.0, event_bus=event_bus)
    except Exception as e:
        logger.warning(f"{worker_prefix}Klik group gagal: {e}")

    if _is_active():
        logger.bot(f"{worker_prefix}Opsi 'Pilih dari Master KBLI' berhasil dipilih (via group).")
        return True

    # Metode 4: JavaScript dispatch click & check pada input
    try:
        logger.bot(f"{worker_prefix}Memicu pemilihan 'Pilih dari Master KBLI' via JavaScript Dispatch...")
        page.evaluate('''() => {
            const inp = document.querySelector("div[id^='kbli_genai#'] input[value='999999']");
            if (inp) {
                inp.checked = true;
                inp.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                inp.dispatchEvent(new Event('change', { bubbles: true }));
                inp.dispatchEvent(new Event('input', { bubbles: true }));
                const parent = inp.closest("div[role='group']");
                if (parent) {
                    const ctrl = parent.querySelector("div[role='radio']");
                    if (ctrl) ctrl.click();
                    const lbl = parent.querySelector("label");
                    if (lbl) lbl.click();
                }
            }
        }''')
        random_sleep(0.8, 1.2, event_bus=event_bus)
    except Exception as e:
        logger.warning(f"{worker_prefix}JS dispatch gagal: {e}")

    if _is_active():
        logger.bot(f"{worker_prefix}Opsi 'Pilih dari Master KBLI' berhasil dipilih (via JS dispatch).")
        return True

    # Metode 5: Force check pada input radio
    try:
        if master_input.count() > 0:
            logger.bot(f"{worker_prefix}Memicu check(force=True) pada input radio 999999...")
            master_input.check(force=True, timeout=5000)
            random_sleep(0.6, 1.0, event_bus=event_bus)
    except Exception as e:
        logger.warning(f"{worker_prefix}Force check gagal: {e}")

    return _is_active()

def _process_kbli_verification(page, kbli_lama, st_kbli, kbli_baru, event_bus=None, worker_prefix=""):
    """
    Memeriksa kondisi KBLI pada rincian kode KBLI (div[id^='kbli_genai#']).
    - Kondisi 1: Radio 'Pilih dari Master KBLI' terpilih -> cek div#kbli vs kbli_akhir
    - Kondisi 2: Radio opsi langsung terpilih -> cek label vs kbli_akhir
    Jika cocok:
      - Status_KBLI 'Tetap' -> Remark #0 pada div#kbli_genai
      - Status_KBLI 'Ganti' -> Ubah Master KBLI ke KBLI_Terbaru -> Remark #4 pada div#kbli_genai
    Return: (success: bool, status_code: str, keterangan: str)
    """
    kbli_genai = page.locator(KBLI_AIR_11502_SELECTORS["container_kbli_genai"]).first
    kbli_genai.wait_for(state="attached", timeout=25000)
    try:
        kbli_genai.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    random_sleep(0.4, 0.8, event_bus=event_bus)

    # Deteksi Kondisi: Apakah radio 'Pilih dari Master KBLI' (value=999999) aktif?
    master_radio_input = kbli_genai.locator("input[value='999999']").first
    master_radio_group = kbli_genai.locator("div[role='group']:has(input[value='999999'])").first

    is_kondisi_1 = False
    if master_radio_input.count() > 0:
        if master_radio_input.is_checked() or master_radio_input.get_attribute("data-checked") is not None:
            is_kondisi_1 = True
        elif master_radio_group.count() > 0 and master_radio_group.get_attribute("data-checked") is not None:
            is_kondisi_1 = True

    kbli_lama_clean = str(kbli_lama or "").strip()
    kbli_lama_5 = kbli_lama_clean.zfill(5) if kbli_lama_clean else ""
    st_norm = str(st_kbli or "").strip().lower()

    if is_kondisi_1:
        logger.bot(f"{worker_prefix}[Kondisi 1] Radio 'Pilih dari Master KBLI' aktif. Memeriksa isian Master KBLI...")
        kbli_master_box = page.locator(KBLI_AIR_11502_SELECTORS["container_master_kbli"]).first
        kbli_master_box.wait_for(state="visible", timeout=15000)

        target_textarea = kbli_master_box.locator(KBLI_AIR_11502_SELECTORS["textarea_master_kbli"]).first
        placeholder = (target_textarea.get_attribute("placeholder") or "").strip()
        val_text = ""
        try:
            val_text = target_textarea.input_value().strip()
        except Exception:
            pass
        if not val_text:
            val_text = (target_textarea.get_attribute("value") or target_textarea.inner_text() or "").strip()

        combined_master = f"{placeholder} {val_text}".strip()

        # Ekstrak 5 digit kode KBLI jika ada (misal dari '[A][01220]Pertanian...' -> '01220')
        kbli_match = re.search(r'\[([0-9]{5})\]', combined_master) or re.search(r'\b([0-9]{5})\b', combined_master)
        web_kbli = kbli_match.group(1) if kbli_match else ""

        logger.info(f"{worker_prefix}[Kondisi 1] Teks Master KBLI web: '{combined_master}' (Kode KBLI web: '{web_kbli or 'tidak terdeteksi'}')")

        # Cek apakah mengandung kbli_akhir
        matched = False
        if web_kbli and (web_kbli == kbli_lama_clean or web_kbli == kbli_lama_5):
            matched = True
        elif kbli_lama_clean and (kbli_lama_clean in combined_master or kbli_lama_5 in combined_master):
            matched = True

        if not matched:
            err_msg = f"KBLI Akhir tidak cocok (Excel: '{kbli_lama_clean}' vs Web: '{web_kbli or combined_master[:35]}')"
            logger.warning(f"⚠️ {worker_prefix}{err_msg} -> Dilewati.")
            return False, "DILEWATI", err_msg

        # Sama -> lanjutkan cek Status_KBLI
        if st_norm == "tetap":
            logger.bot(f"{worker_prefix}Status KBLI 'Tetap'. Memberikan Catatan #0 pada rincian kbli_genai...")
            add_remarks_to_element(page, KBLI_AIR_11502_SELECTORS["container_kbli_genai"], "#0", event_bus=event_bus, worker_prefix=worker_prefix)
            _add_remarks_to_master_kbli_if_visible(page, "#0", KBLI_AIR_11502_SELECTORS["container_master_kbli"], event_bus=event_bus, worker_prefix=worker_prefix)
            return True, "SUKSES", f"KBLI Tetap ({kbli_lama_clean}) diremark #0"
        elif st_norm == "ganti":
            logger.bot(f"{worker_prefix}Status KBLI 'Ganti'. Mengubah Master KBLI ke '{kbli_baru}'...")
            _fill_master_kbli(page, kbli_baru, event_bus=event_bus, worker_prefix=worker_prefix)
            logger.bot(f"{worker_prefix}Memberikan Catatan #4 pada rincian kbli_genai...")
            add_remarks_to_element(page, KBLI_AIR_11502_SELECTORS["container_kbli_genai"], "#4", event_bus=event_bus, worker_prefix=worker_prefix)
            _add_remarks_to_master_kbli_if_visible(page, "#4", KBLI_AIR_11502_SELECTORS["container_master_kbli"], event_bus=event_bus, worker_prefix=worker_prefix)
            return True, "SUKSES", f"KBLI Diganti ({kbli_lama_clean} -> {kbli_baru}) diremark #4"
        else:
            return False, "DILEWATI", f"Status_KBLI '{st_kbli}' tidak valid (hanya 'Tetap' atau 'Ganti')"

    else:
        logger.bot(f"{worker_prefix}[Kondisi 2] Opsi radio KBLI terpilih langsung. Memeriksa label opsi...")
        # Cari item radio yang terpilih (selain value=999999)
        checked_radio_elem = kbli_genai.locator(
            "div[role='group'][data-checked]:not(:has(input[value='999999'])), "
            "input[type='radio'][data-checked]:not([value='999999'])"
        ).first

        if checked_radio_elem.count() == 0:
            all_radios = kbli_genai.locator("input[type='radio']")
            for i in range(all_radios.count()):
                r = all_radios.nth(i)
                val = r.get_attribute("value") or ""
                if val != "999999" and (r.is_checked() or r.get_attribute("data-checked") is not None):
                    checked_radio_elem = r.locator("xpath=parent::*")
                    break

        if checked_radio_elem.count() == 0:
            raise Exception("Tidak ditemukan opsi radio KBLI yang aktif pada rincian kbli_genai")

        checked_label = checked_radio_elem.inner_text().strip()
        kbli_match = re.search(r'\[([0-9]{5})\]', checked_label) or re.search(r'\b([0-9]{5})\b', checked_label)
        web_kbli = kbli_match.group(1) if kbli_match else ""

        logger.info(f"{worker_prefix}[Kondisi 2] Label opsi KBLI aktif: '{checked_label}' (Kode KBLI web: '{web_kbli or 'tidak terdeteksi'}')")

        # Cek apakah mengandung kbli_akhir
        matched = False
        if web_kbli and (web_kbli == kbli_lama_clean or web_kbli == kbli_lama_5):
            matched = True
        elif kbli_lama_clean and (kbli_lama_clean in checked_label or kbli_lama_5 in checked_label):
            matched = True

        if not matched:
            err_msg = f"KBLI Akhir tidak cocok (Excel: '{kbli_lama_clean}' vs Web: '{web_kbli or checked_label[:35]}')"
            logger.warning(f"⚠️ {worker_prefix}{err_msg} -> Dilewati.")
            return False, "DILEWATI", err_msg

        # Sama -> lanjutkan cek Status_KBLI
        if st_norm == "tetap":
            logger.bot(f"{worker_prefix}Status KBLI 'Tetap'. Memberikan Catatan #0 pada rincian kbli_genai...")
            add_remarks_to_element(page, KBLI_AIR_11502_SELECTORS["container_kbli_genai"], "#0", event_bus=event_bus, worker_prefix=worker_prefix)
            _add_remarks_to_master_kbli_if_visible(page, "#0", KBLI_AIR_11502_SELECTORS["container_master_kbli"], event_bus=event_bus, worker_prefix=worker_prefix)
            return True, "SUKSES", f"KBLI Tetap ({kbli_lama_clean}) diremark #0"
        elif st_norm == "ganti":
            logger.bot(f"{worker_prefix}Status KBLI 'Ganti' pada Kondisi 2. Memilih opsi 'Pilih dari Master KBLI'...")
            ok_select = _select_master_kbli_radio(page, kbli_genai, event_bus=event_bus, worker_prefix=worker_prefix)
            if not ok_select:
                raise Exception("Gagal mengaktifkan opsi 'Pilih dari Master KBLI' pada rincian kbli_genai")

            # Tunggu elemen master kbli muncul
            logger.bot(f"{worker_prefix}Menunggu rincian form Master KBLI muncul...")
            master_box = page.locator(KBLI_AIR_11502_SELECTORS["container_master_kbli"]).first
            master_box.wait_for(state="visible", timeout=15000)
            _fill_master_kbli(page, kbli_baru, event_bus=event_bus, worker_prefix=worker_prefix)

            logger.bot(f"{worker_prefix}Memberikan Catatan #4 pada rincian kbli_genai...")
            add_remarks_to_element(page, KBLI_AIR_11502_SELECTORS["container_kbli_genai"], "#4", event_bus=event_bus, worker_prefix=worker_prefix)
            _add_remarks_to_master_kbli_if_visible(page, "#4", KBLI_AIR_11502_SELECTORS["container_master_kbli"], event_bus=event_bus, worker_prefix=worker_prefix)
            return True, "SUKSES", f"KBLI Diganti ({kbli_lama_clean} -> {kbli_baru}) diremark #4"
        else:
            return False, "DILEWATI", f"Status_KBLI '{st_kbli}' tidak valid (hanya 'Tetap' atau 'Ganti')"

def _is_any_radio_selected(container):
    """Memeriksa apakah ada salah satu radio button yang sudah terpilih di dalam container."""
    try:
        # 1. Cek input radio dengan :checked atau data-checked
        checked_inputs = container.locator("input[type='radio']:checked, input[type='radio'][data-checked]")
        if checked_inputs.count() > 0:
            return True
        # 2. Cek pembungkus role='group' atau role='radio' yang memiliki data-checked atau aria-checked='true'
        checked_controls = container.locator("div[role='group'][data-checked], div[role='radio'][data-checked], div[role='radio'][aria-checked='true']")
        if checked_controls.count() > 0:
            return True
        # 3. Cek indicator aktif di dalam container
        indicators = container.locator("div[id$='-indicator'][data-checked], div[id$='-indicator']")
        if indicators.count() > 0:
            for i in range(indicators.count()):
                ind = indicators.nth(i)
                if ind.is_visible():
                    return True
    except Exception:
        pass
    return False

def _select_radio_option(page, container, option_label_text, option_value="3", event_bus=None, worker_prefix=""):
    """
    Memilih opsi radio button tertentu di dalam container
    dengan multi-stage fallback (label -> radio control -> group -> JS dispatch -> force check).
    """
    val_str = str(option_value).strip()
    val_alt = val_str.lstrip("0") if val_str.startswith("0") and len(val_str) > 1 else (f"0{val_str}" if len(val_str) == 1 else val_str)

    target_input = container.locator(
        f"input[type='radio'][value='{val_str}'], "
        f"input[type='radio'][value='{val_alt}']"
    ).first
    target_label = container.locator(f"label:has-text('{option_label_text}')").first
    target_control = container.locator(
        f"div[role='radio']:has(+ label:has-text('{option_label_text}')), "
        f"div[role='group']:has(input[value='{val_str}']) div[role='radio'], "
        f"div[role='group']:has(input[value='{val_alt}']) div[role='radio']"
    ).first
    target_group = container.locator(
        f"div[role='group']:has(input[value='{val_str}']), "
        f"div[role='group']:has(input[value='{val_alt}'])"
    ).first

    def _is_target_active():
        try:
            if target_input.count() > 0:
                if target_input.is_checked() or target_input.get_attribute("data-checked") is not None:
                    return True
            if target_group.count() > 0 and target_group.get_attribute("data-checked") is not None:
                return True
            if target_control.count() > 0 and target_control.get_attribute("data-checked") is not None:
                return True
            if target_label.count() > 0 and target_label.get_attribute("data-checked") is not None:
                return True
        except Exception:
            pass
        return False

    if _is_target_active():
        return True

    # 1. Scroll into view
    try:
        target_label.scroll_into_view_if_needed(timeout=4000)
    except Exception:
        try:
            container.scroll_into_view_if_needed(timeout=4000)
        except Exception:
            pass

    random_sleep(0.2, 0.4, event_bus=event_bus)

    # Metode 1: Klik label
    try:
        if target_label.count() > 0 and target_label.is_visible():
            target_label.click(timeout=5000)
            random_sleep(0.4, 0.7, event_bus=event_bus)
    except Exception:
        pass

    if _is_target_active():
        return True

    # Metode 2: Klik div role='radio'
    try:
        if target_control.count() > 0 and target_control.is_visible():
            target_control.click(timeout=5000)
            random_sleep(0.4, 0.7, event_bus=event_bus)
    except Exception:
        pass

    if _is_target_active():
        return True

    # Metode 3: Klik pembungkus group
    try:
        if target_group.count() > 0 and target_group.is_visible():
            target_group.click(timeout=5000)
            random_sleep(0.4, 0.7, event_bus=event_bus)
    except Exception:
        pass

    if _is_target_active():
        return True

    # Metode 4: JavaScript dispatch click & check
    try:
        container_id = container.get_attribute("id") or ""
        page.evaluate('''([cid, val, valAlt]) => {
            const root = cid ? document.getElementById(cid) : document;
            if (!root) return;
            const inp = root.querySelector(`input[type='radio'][value='${val}']`) ||
                        root.querySelector(`input[type='radio'][value='${valAlt}']`);
            if (inp) {
                inp.checked = true;
                inp.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                inp.dispatchEvent(new Event('change', { bubbles: true }));
                inp.dispatchEvent(new Event('input', { bubbles: true }));
                const parent = inp.closest("div[role='group']");
                if (parent) {
                    const ctrl = parent.querySelector("div[role='radio']");
                    if (ctrl) ctrl.click();
                    const lbl = parent.querySelector("label");
                    if (lbl) lbl.click();
                }
            }
        }''', [container_id, val_str, val_alt])
        random_sleep(0.5, 0.8, event_bus=event_bus)
    except Exception:
        pass

    if _is_target_active():
        return True

    # Metode 5: Force check pada input
    try:
        if target_input.count() > 0:
            target_input.check(force=True, timeout=5000)
            random_sleep(0.4, 0.7, event_bus=event_bus)
    except Exception:
        pass

    return _is_target_active()

def _fill_textarea_field(page, container, selector_input, text_value, field_name="", event_bus=None, worker_prefix=""):
    """
    Mengisi elemen textarea atau text field di dalam container dengan multi-stage fallback:
    1. Pastikan elemen terlihat & scroll into view
    2. Periksa apakah sudah terisi sesuai
    3. Direct fill + dispatch input & change event
    4. Fallback sequential typing (Ctrl+A -> Backspace -> press_sequentially)
    5. Fallback JavaScript dispatch
    6. Verifikasi akhir nilai input
    """
    target = container.locator(selector_input).first
    try:
        target.wait_for(state="attached", timeout=15000)
    except Exception as e:
        logger.warning(f"⚠️ {worker_prefix}Elemen textarea/input '{field_name}' tidak ditemukan di DOM: {e}")
        return False, f"Elemen '{field_name}' tidak ditemukan"

    try:
        target.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass

    try:
        target.wait_for(state="visible", timeout=10000)
    except Exception:
        pass

    # Cek nilai saat ini
    curr_val = ""
    try:
        curr_val = (target.input_value() or target.get_attribute("value") or target.inner_text() or "").strip()
    except Exception:
        pass

    target_norm = normalize_text(text_value)
    if curr_val and normalize_text(curr_val) == target_norm:
        logger.bot(f"{worker_prefix}[{field_name}] Sudah terisi sesuai ('{curr_val}').")
        return True, f"Sudah terisi '{curr_val}'"

    logger.bot(f"{worker_prefix}[{field_name}] Mengisi teks '{text_value}'...")

    # Metode 1: Click & direct fill
    try:
        target.click(timeout=6000)
        human_jitter(0.1, 0.2, event_bus=event_bus)
        target.fill(text_value)
        target.dispatch_event("input")
        target.dispatch_event("change")
    except Exception as e:
        logger.warning(f"{worker_prefix}Direct fill '{field_name}' gagal: {e}")

    # Cek hasil metode 1
    new_val = ""
    try:
        new_val = (target.input_value() or target.get_attribute("value") or "").strip()
    except Exception:
        pass

    if normalize_text(new_val) == target_norm:
        logger.bot(f"{worker_prefix}[{field_name}] Berhasil diisi via direct fill.")
        try:
            page.keyboard.press("Tab")
        except Exception:
            pass
        return True, "Berhasil diisi"

    # Metode 2: Select all + press_sequentially
    try:
        logger.bot(f"{worker_prefix}[{field_name}] Mencoba metode sequential typing...")
        target.click(timeout=5000)
        try:
            target.select_text(timeout=2000)
        except Exception:
            page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        target.press_sequentially(text_value, delay=35)
        target.dispatch_event("input")
        target.dispatch_event("change")
    except Exception as e:
        logger.warning(f"{worker_prefix}Sequential typing '{field_name}' gagal: {e}")

    try:
        new_val = (target.input_value() or target.get_attribute("value") or "").strip()
    except Exception:
        pass

    if normalize_text(new_val) == target_norm:
        logger.bot(f"{worker_prefix}[{field_name}] Berhasil diisi via sequential typing.")
        try:
            page.keyboard.press("Tab")
        except Exception:
            pass
        return True, "Berhasil diisi"

    # Metode 3: JavaScript dispatch value
    try:
        logger.bot(f"{worker_prefix}[{field_name}] Mencoba pengisian via JavaScript dispatch...")
        cid = container.get_attribute("id") or ""
        page.evaluate('''([cid, val]) => {
            const root = cid ? document.getElementById(cid) : document;
            if (!root) return;
            const el = root.querySelector("textarea, input[type='text']");
            if (el) {
                el.value = val;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }''', [cid, text_value])
        random_sleep(0.3, 0.5, event_bus=event_bus)
    except Exception as e:
        logger.warning(f"{worker_prefix}JS dispatch '{field_name}' gagal: {e}")

    try:
        new_val = (target.input_value() or target.get_attribute("value") or "").strip()
    except Exception:
        pass

    if normalize_text(new_val) == target_norm:
        logger.bot(f"{worker_prefix}[{field_name}] Berhasil diisi via JavaScript.")
        try:
            page.keyboard.press("Tab")
        except Exception:
            pass
        return True, "Berhasil diisi"

    return False, f"Gagal memverifikasi isian '{field_name}' (terbaca: '{new_val}')"

def _process_air_11502_characteristics(page, event_bus=None, worker_prefix=""):
    """
    Menjalankan pengisian karakteristik usaha spesifik KBLI Air 11502 (Air Minum Isi Ulang):
    Step 1: Rincian memproduksi barang sendiri (13. b1) -> Pilih 1. Ya (value='1')
    Step 2: Rincian menyediakan layanan makan minum (13. b2) -> Pilih 2. Tidak (value='2')
    Step 3: Rincian input yang digunakan (13. d) -> Isikan "AIR BAKU"
    Step 4: Rincian proses yang dilakukan (13. e) -> Isikan "PENYARINGAN AIR DAN PENGISIAN AIR KE GALON"

    Return: (success: bool, status_code: str, keterangan: str)
    """
    # --------------------------------------------------------------------------
    # Step 1: 13. b1 Memproduksi Barang Sendiri -> 1. Ya (value='1')
    # --------------------------------------------------------------------------
    if event_bus and event_bus.is_stop_requested():
        return False, "DIHENTIKAN", "Dihentikan oleh pengguna saat pengisian karakteristik usaha"

    logger.bot(f"{worker_prefix}[13. b1] Memeriksa rincian Memproduksi Barang Sendiri...")
    c_b1 = page.locator(KBLI_AIR_11502_SELECTORS["container_produk_sendiri"]).first
    try:
        c_b1.wait_for(state="attached", timeout=15000)
        c_b1.scroll_into_view_if_needed(timeout=4000)
    except Exception:
        logger.warning(f"⚠️ {worker_prefix}[13. b1] Container produk_sendiri tidak ditemukan.")
        return False, "DILEWATI", "Rincian 13. b1 (Memproduksi Barang) tidak ditemukan pada formulir"

    random_sleep(0.2, 0.4, event_bus=event_bus)
    ok_b1 = _select_radio_option(
        page, c_b1, option_label_text="Ya", option_value="1",
        event_bus=event_bus, worker_prefix=worker_prefix
    )
    if not ok_b1:
        logger.warning(f"⚠️ {worker_prefix}[13. b1] Gagal memilih opsi '1. Ya'.")
        return False, "GAGAL", "Gagal memilih '1. Ya' pada rincian 13. b1 (Memproduksi Barang)"
    logger.bot(f"{worker_prefix}[13. b1] Opsi '1. Ya' aktif/berhasil dipilih.")
    random_sleep(0.5, 0.8, event_bus=event_bus)

    # --------------------------------------------------------------------------
    # Step 2: 13. b2 Layanan Makan Minum -> 2. Tidak (value='2')
    # --------------------------------------------------------------------------
    if event_bus and event_bus.is_stop_requested():
        return False, "DIHENTIKAN", "Dihentikan oleh pengguna saat pengisian karakteristik usaha"

    logger.bot(f"{worker_prefix}[13. b2] Memeriksa rincian Layanan Makan Minum...")
    c_b2 = page.locator(KBLI_AIR_11502_SELECTORS["container_layanan_mamin"]).first
    try:
        c_b2.wait_for(state="attached", timeout=12000)
        c_b2.scroll_into_view_if_needed(timeout=4000)
    except Exception:
        logger.warning(f"⚠️ {worker_prefix}[13. b2] Container layanan_mamin tidak ditemukan.")
        return False, "DILEWATI", "Rincian 13. b2 (Layanan Makan Minum) tidak ditemukan pada formulir"

    random_sleep(0.2, 0.4, event_bus=event_bus)
    ok_b2 = _select_radio_option(
        page, c_b2, option_label_text="Tidak", option_value="2",
        event_bus=event_bus, worker_prefix=worker_prefix
    )
    if not ok_b2:
        logger.warning(f"⚠️ {worker_prefix}[13. b2] Gagal memilih opsi '2. Tidak'.")
        return False, "GAGAL", "Gagal memilih '2. Tidak' pada rincian 13. b2 (Layanan Makan Minum)"
    logger.bot(f"{worker_prefix}[13. b2] Opsi '2. Tidak' aktif/berhasil dipilih.")
    random_sleep(0.5, 0.8, event_bus=event_bus)

    # --------------------------------------------------------------------------
    # Step 3: 13. d Input yang Digunakan -> "AIR BAKU"
    # --------------------------------------------------------------------------
    if event_bus and event_bus.is_stop_requested():
        return False, "DIHENTIKAN", "Dihentikan oleh pengguna saat pengisian karakteristik usaha"

    logger.bot(f"{worker_prefix}[13. d] Memeriksa rincian Input yang Digunakan...")
    c_input = page.locator(KBLI_AIR_11502_SELECTORS["container_input"]).first
    try:
        c_input.wait_for(state="attached", timeout=15000)
        c_input.scroll_into_view_if_needed(timeout=4000)
    except Exception:
        logger.warning(f"⚠️ {worker_prefix}[13. d] Container input tidak muncul pada formulir.")
        return False, "DILEWATI", "Rincian 13. d (Input yang Digunakan) tidak muncul pada formulir"

    ok_input, msg_input = _fill_textarea_field(
        page, c_input,
        selector_input=KBLI_AIR_11502_SELECTORS["textarea_input"],
        text_value="AIR BAKU",
        field_name="13. d Input yang Digunakan",
        event_bus=event_bus,
        worker_prefix=worker_prefix
    )
    if not ok_input:
        logger.warning(f"⚠️ {worker_prefix}[13. d] {msg_input}")
        return False, "GAGAL", f"Gagal mengisi 13. d (Input): {msg_input}"
    random_sleep(0.4, 0.7, event_bus=event_bus)

    # --------------------------------------------------------------------------
    # Step 4: 13. e Proses yang Dilakukan -> "PENYARINGAN AIR DAN PENGISIAN AIR KE GALON"
    # --------------------------------------------------------------------------
    if event_bus and event_bus.is_stop_requested():
        return False, "DIHENTIKAN", "Dihentikan oleh pengguna saat pengisian karakteristik usaha"

    logger.bot(f"{worker_prefix}[13. e] Memeriksa rincian Proses yang Dilakukan...")
    c_proses = page.locator(KBLI_AIR_11502_SELECTORS["container_proses"]).first
    try:
        c_proses.wait_for(state="attached", timeout=15000)
        c_proses.scroll_into_view_if_needed(timeout=4000)
    except Exception:
        logger.warning(f"⚠️ {worker_prefix}[13. e] Container proses tidak muncul pada formulir.")
        return False, "DILEWATI", "Rincian 13. e (Proses yang Dilakukan) tidak muncul pada formulir"

    ok_proses, msg_proses = _fill_textarea_field(
        page, c_proses,
        selector_input=KBLI_AIR_11502_SELECTORS["textarea_proses"],
        text_value="PENYARINGAN AIR DAN PENGISIAN AIR KE GALON",
        field_name="13. e Proses yang Dilakukan",
        event_bus=event_bus,
        worker_prefix=worker_prefix
    )
    if not ok_proses:
        logger.warning(f"⚠️ {worker_prefix}[13. e] {msg_proses}")
        return False, "GAGAL", f"Gagal mengisi 13. e (Proses): {msg_proses}"
    random_sleep(0.5, 0.8, event_bus=event_bus)

    logger.bot(f"{worker_prefix}Seluruh karakteristik usaha KBLI Air 11502 (13. b1, 13. b2, 13. d, 13. e) berhasil diproses.")
    return True, "SUKSES", "Karakteristik usaha KBLI Air 11502 berhasil diisi"

# Alias untuk kompatibilitas
_process_air_11052_characteristics = _process_air_11502_characteristics

def _check_and_fill_halal(page, event_bus=None, worker_prefix=""):
    """
    Step Mengecek rincian produk halal:
    1. Cek apakah ada rincian tentang Menghasilkan produk bersertifikat halal (id halal).
    2. Jika tidak ada, abaikan/lanjut. Jika ada, scroll ke rincian tersebut.
       Cek apakah pilihan radio buttonnya sudah ada yang dipilih. Jika sudah ada, lanjut (jangan diubah).
    3. Jika belum ada yang dipilih, pilih radio button '3. Tidak/Belum'.
    4. Setelah klik, akan muncul rincian jumlah produk yang belum halal (id belum_halal).
    5. Isikan jumlah pada rincian belum_halal sejumlah 1 (jika belum terisi).
    """
    if event_bus and event_bus.is_stop_requested():
        return

    try:
        halal_container = page.locator(KBLI_AIR_11502_SELECTORS["container_halal"]).first
        if halal_container.count() == 0:
            return

        try:
            halal_container.wait_for(state="attached", timeout=2000)
        except Exception:
            return

        logger.bot(f"{worker_prefix}Memeriksa rincian Produk Halal (19.a)...")
        try:
            halal_container.scroll_into_view_if_needed(timeout=4000)
        except Exception:
            pass
        random_sleep(0.3, 0.5, event_bus=event_bus)

        # Cek apakah sudah ada radio yang terpilih
        if _is_any_radio_selected(halal_container):
            logger.bot(f"{worker_prefix}Rincian Produk Halal sudah terisi sebelumnya. Melewati pengisian.")
            return

        # Belum ada yang dipilih -> pilih opsi '3. Tidak/Belum'
        logger.bot(f"{worker_prefix}Rincian Produk Halal belum dipilih. Memilih opsi '3. Tidak/Belum'...")
        success = _select_radio_option(page, halal_container, option_label_text="Tidak/Belum", option_value="3", event_bus=event_bus, worker_prefix=worker_prefix)
        if not success:
            logger.warning(f"⚠️ {worker_prefix}Gagal memastikan opsi '3. Tidak/Belum' terpilih pada rincian halal.")

        random_sleep(0.5, 0.8, event_bus=event_bus)

        # Cek rincian belum_halal yang muncul
        belum_halal_container = page.locator(KBLI_AIR_11502_SELECTORS["container_belum_halal"]).first
        try:
            belum_halal_container.wait_for(state="attached", timeout=5000)
            belum_halal_container.scroll_into_view_if_needed(timeout=4000)
        except Exception:
            pass

        inp_belum_halal = belum_halal_container.locator(KBLI_AIR_11502_SELECTORS["input_belum_halal"]).first
        if inp_belum_halal.count() > 0:
            inp_belum_halal.wait_for(state="visible", timeout=5000)
            curr_val = ""
            try:
                curr_val = inp_belum_halal.input_value() or inp_belum_halal.get_attribute("value") or ""
            except Exception:
                pass

            if curr_val.strip():
                logger.bot(f"{worker_prefix}Rincian belum_halal sudah memiliki isian: '{curr_val.strip()}'. Tidak diubah.")
            else:
                logger.bot(f"{worker_prefix}Mengisi rincian belum_halal (19.c) sejumlah 1...")
                inp_belum_halal.fill("1")
                try:
                    inp_belum_halal.dispatch_event("input")
                    inp_belum_halal.dispatch_event("change")
                except Exception:
                    pass
                random_sleep(0.3, 0.6, event_bus=event_bus)
    except Exception as e:
        logger.warning(f"⚠️ {worker_prefix}Peringatan saat pengecekan rincian halal: {e}")

def _check_and_fill_izin_edar(page, event_bus=None, worker_prefix=""):
    """
    Step Mengecek rincian izin edar:
    1. Cek apakah ada rincian tentang memiliki izin edar (id izin_edar).
    2. Jika tidak ada, abaikan/lanjut. Jika ada, scroll ke rincian tersebut.
       Cek apakah pada pilihan radio buttonnya sudah ada yang dipilih. Jika sudah ada, lanjut (jangan diubah).
    3. Jika belum ada yang dipilih, maka pilih radio button '3. Tidak'.
    4. Setelah klik, akan muncul rincian jumlah produk yang belum izin edar (id belum_bpom).
    5. Isikan jumlah pada rincian belum_bpom sejumlah 1 (jika belum terisi).
    """
    if event_bus and event_bus.is_stop_requested():
        return

    try:
        edar_container = page.locator(KBLI_AIR_11502_SELECTORS["container_izin_edar"]).first
        if edar_container.count() == 0:
            return

        try:
            edar_container.wait_for(state="attached", timeout=2000)
        except Exception:
            return

        logger.bot(f"{worker_prefix}Memeriksa rincian Izin Edar (20.a)...")
        try:
            edar_container.scroll_into_view_if_needed(timeout=4000)
        except Exception:
            pass
        random_sleep(0.3, 0.5, event_bus=event_bus)

        # Cek apakah sudah ada radio yang terpilih
        if _is_any_radio_selected(edar_container):
            logger.bot(f"{worker_prefix}Rincian Izin Edar sudah terisi sebelumnya. Melewati pengisian.")
            return

        # Belum ada yang dipilih -> pilih opsi '3. Tidak'
        logger.bot(f"{worker_prefix}Rincian Izin Edar belum dipilih. Memilih opsi '3. Tidak'...")
        success = _select_radio_option(page, edar_container, option_label_text="Tidak", option_value="3", event_bus=event_bus, worker_prefix=worker_prefix)
        if not success:
            logger.warning(f"⚠️ {worker_prefix}Gagal memastikan opsi '3. Tidak' terpilih pada rincian izin edar.")

        random_sleep(0.5, 0.8, event_bus=event_bus)

        # Cek rincian belum_bpom yang muncul
        belum_bpom_container = page.locator(KBLI_AIR_11502_SELECTORS["container_belum_bpom"]).first
        try:
            belum_bpom_container.wait_for(state="attached", timeout=5000)
            belum_bpom_container.scroll_into_view_if_needed(timeout=4000)
        except Exception:
            pass

        inp_belum_bpom = belum_bpom_container.locator(KBLI_AIR_11502_SELECTORS["input_belum_bpom"]).first
        if inp_belum_bpom.count() > 0:
            inp_belum_bpom.wait_for(state="visible", timeout=5000)
            curr_val = ""
            try:
                curr_val = inp_belum_bpom.input_value() or inp_belum_bpom.get_attribute("value") or ""
            except Exception:
                pass

            if curr_val.strip():
                logger.bot(f"{worker_prefix}Rincian belum_bpom sudah memiliki isian: '{curr_val.strip()}'. Tidak diubah.")
            else:
                logger.bot(f"{worker_prefix}Mengisi rincian belum_bpom (20.c) sejumlah 1...")
                inp_belum_bpom.fill("1")
                try:
                    inp_belum_bpom.dispatch_event("input")
                    inp_belum_bpom.dispatch_event("change")
                except Exception:
                    pass
                random_sleep(0.3, 0.6, event_bus=event_bus)
    except Exception as e:
        logger.warning(f"⚠️ {worker_prefix}Peringatan saat pengecekan rincian izin edar: {e}")

def _submit_assignment_form(page, event_bus=None, worker_prefix="", debug_review=False, auto_minimize=True, row_idx=None, keg_utama=""):
    """
    Menjalankan alur submit formulir Fasih (Kirim -> Cek Galat -> Konfirmasi -> Berhasil).
    """
    # 0. Cek & Isi Rincian Produk Halal dan Izin Edar (masih di formulir rincian usaha sebelum pindah ke Blok Catatan)
    _check_and_fill_halal(page, event_bus=event_bus, worker_prefix=worker_prefix)
    _check_and_fill_izin_edar(page, event_bus=event_bus, worker_prefix=worker_prefix)

    # 1. Menuju Blok Catatan di sidebar (jika ada)
    try:
        blok_catatan = page.locator(KBLI_AIR_11502_SELECTORS["sidebar_blok_catatan"]).first
        if blok_catatan.is_visible(timeout=5000):
            logger.bot(f"{worker_prefix}Menuju Blok Catatan di sidebar...")
            safe_click(page, blok_catatan, timeout=10000, event_bus=event_bus)
            random_sleep(1.0, 1.6, event_bus=event_bus)
    except Exception:
        pass

    # 2. Pastikan switch toggle anomali aktif jika ada di Blok Catatan
    try:
        box = page.locator("div#cek_anomali_button").first
        if box.is_visible(timeout=3000):
            sw_input = box.locator("input[role='switch']").first
            sw_control = box.locator("[id^='switch-'][id$='-control']").first
            if sw_input.get_attribute("aria-checked") != "true":
                logger.bot(f"{worker_prefix}Mengaktifkan switch 'Tampilkan Anomali Usaha dan Keluarga'...")
                safe_click(page, sw_control, timeout=5000, event_bus=event_bus)
                random_sleep(0.6, 1.0, event_bus=event_bus)
    except Exception:
        pass

    # 3. Klik Kirim pada formulir Fasih
    logger.bot(f"{worker_prefix}[1/4] Mengklik tombol Kirim formulir Fasih...")
    form_kirim_btn = page.locator(KBLI_AIR_11502_SELECTORS["btn_kirim"]).first
    form_kirim_btn.wait_for(state="attached", timeout=25000)
    safe_click(page, form_kirim_btn, timeout=25000, event_bus=event_bus, force=True)
    random_sleep(1.0, 1.8, event_bus=event_bus, allow_hesitation=False)

    # 4. Dialog Pop-up Validasi Kirim
    btn_konfirmasi = page.locator(KBLI_AIR_11502_SELECTORS["btn_konfirmasi_kirim"]).last
    if not btn_konfirmasi.is_visible(timeout=2500):
        logger.bot(f"{worker_prefix}[2/4] Menunggu pop-up validasi Kirim...")
        dialog = page.locator("div[role='dialog'], div[role='alertdialog'], div:has(button:has-text('Batal')):has(button:has-text('Kirim'))").last
        dialog.wait_for(state="visible", timeout=25000)
        random_sleep(0.5, 0.8, event_bus=event_bus, allow_hesitation=False)

        # Cek jumlah Galat
        galat_count = 0
        try:
            galat_card = dialog.locator("button:has-text('Galat')").first
            if galat_card.count() > 0 and galat_card.is_visible():
                card_text = galat_card.inner_text().strip()
                for line in card_text.split("\n"):
                    if line.strip().isdigit():
                        galat_count = int(line.strip())
                        break
                else:
                    nums = re.findall(r"\b\d+\b", card_text)
                    if nums:
                        galat_count = int(nums[0])
            else:
                span_num = dialog.locator("xpath=.//*[text()='Galat']/following-sibling::*[1]").first
                if span_num.count() > 0 and span_num.inner_text().strip().isdigit():
                    galat_count = int(span_num.inner_text().strip())
        except Exception:
            pass

        if galat_count > 0:
            err_msg = f"Terdapat {galat_count} Galat pada form. Submit dibatalkan."
            logger.warning(f"⚠️ {worker_prefix}{err_msg}")
            try:
                btn_batal = dialog.locator("button:has-text('Batal')").first
                if btn_batal.is_visible(timeout=3000):
                    safe_click(page, btn_batal, timeout=5000, event_bus=event_bus)
                else:
                    page.keyboard.press("Escape")
            except Exception:
                page.keyboard.press("Escape")
            return False, f"GAGAL ({galat_count} Galat)", err_msg

        logger.bot(f"{worker_prefix}[2/4] Galat = 0. Mengklik tombol Kirim pada dialog validasi...")
        btn_kirim_dialog = dialog.locator("button:has-text('Kirim')").last
        safe_click(page, btn_kirim_dialog, timeout=20000, event_bus=event_bus)
        random_sleep(1.5, 2.2, event_bus=event_bus, allow_hesitation=False)

    # 5. Dialog Konfirmasi Kirim
    logger.bot(f"{worker_prefix}[3/4] Menunggu dialog Konfirmasi Kirim...")
    btn_konfirmasi = page.locator(KBLI_AIR_11502_SELECTORS["btn_konfirmasi_kirim"]).last
    btn_konfirmasi.wait_for(state="visible", timeout=30000)
    random_sleep(0.5, 1.0, event_bus=event_bus, allow_hesitation=False)

    if debug_review:
        logger.warning(f"🔍 [MODE REVIEW DEBUGGING] {worker_prefix}Baris {row_idx} [{keg_utama}]: Modal Konfirmasi Kirim terbuka.")
        logger.info("Silakan periksa browser. Klik '✅ Konfirmasi Submit & Lanjut' di aplikasi untuk mengirimkan.")
        WindowController.restore_and_focus_browser()
        event_bus.emit("waiting_confirm_submit", {
            "row_idx": row_idx,
            "nama_usaha": keg_utama,
            "worker_id": worker_prefix
        })
        event_bus.wait_for_submit_confirmation()
        if event_bus.is_stop_requested():
            return False, "DIHENTIKAN", "Dihentikan oleh pengguna saat review konfirmasi"
        safe_click(page, btn_konfirmasi, timeout=20000, event_bus=event_bus, force=True)
        if auto_minimize:
            WindowController.minimize_browser()
    else:
        logger.bot(f"{worker_prefix}[3/4] Mengklik tombol Konfirmasi...")
        safe_click(page, btn_konfirmasi, timeout=20000, event_bus=event_bus, force=True)

    # 6. Menunggu dialog sukses
    logger.bot(f"{worker_prefix}[4/4] Menunggu respon submit Fasih...")
    try:
        success_dialog = page.locator(KBLI_AIR_11502_SELECTORS["dialog_sukses"]).first
        success_dialog.wait_for(state="visible", timeout=40000)
        logger.success(f"{worker_prefix}Assignment berhasil disubmit.")
    except Exception:
        logger.warning(f"{worker_prefix}Dialog sukses tidak terdeteksi eksplisit, melanjutkan...")

    return True, "SUKSES", "Assignment berhasil disubmit"

# ==============================================================================
# ENGINE OTOMASI KBLI AIR 11502 (MULTI-WORKER RUNNER)
# ==============================================================================

class SessionExpiredException(Exception):
    """Exception khusus saat sesi Fasih SSO kedaluwarsa atau belum terotentikasi di tengah jalan."""
    pass

class KBLIAir11502Engine:
    def __init__(self, excel_path, event_bus, config_options=None):
        self.excel_path = excel_path
        self.event_bus = event_bus
        self.config_options = config_options or {}
        self.auto_minimize = self.config_options.get("auto_minimize", True)
        self.debug_review_submit = self.config_options.get("debug_review_submit", False)
        self.row_start = self.config_options.get("row_start", 2)
        self.row_end = self.config_options.get("row_end", None)

        # Konfigurasi Mode Login SSO
        self.auth_mode = self.config_options.get("auth_mode", "manual")  # "manual" | "auto"
        self.sso_username = self.config_options.get("sso_username", "").strip()
        self.sso_password = self.config_options.get("sso_password", "").strip()

        # Konfigurasi Multi-Worker (1 s.d. 5 worker)
        raw_workers = self.config_options.get("num_workers", 2)
        try:
            self.num_workers = max(1, min(5, int(raw_workers)))
        except (ValueError, TypeError):
            self.num_workers = 2

        # Browser & CDP options
        self.browser_type = self.config_options.get("browser_type") or BrowserManager.get_active_browser()
        self.incognito = self.config_options.get("incognito") if self.config_options.get("incognito") is not None else BrowserManager.is_incognito_active()
        self.cdp_url = self.config_options.get("cdp_url") or BrowserManager.get_cdp_url(self.browser_type)

        if self.debug_review_submit and self.num_workers > 1:
            logger.warning("⚠️ Mode Review Debugging aktif: Jumlah worker disetel ke 1 agar review dapat dilakukan teratur.")
            self.num_workers = 1

        # Thread synchronization locks
        self.excel_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        self.reauth_lock = threading.Lock()
        self.task_queue = queue.Queue()

        # Shared session statistics
        self.done_session = 0
        self.error_count = 0
        self.skipped_count = 0
        self.processed_count = 0

    def check_pause_and_stop(self, row_idx=None, audit_data=None, worker_id=None):
        """Memeriksa sinyal jeda atau henti secara responsif di setiap tahapan."""
        if self.event_bus.is_stop_requested():
            if row_idx and audit_data:
                audit_data["status"] = "DIHENTIKAN"
                audit_data["keterangan"] = "Dihentikan oleh pengguna"
                self.event_bus.emit("row_completed", {
                    "row_idx": row_idx,
                    "status": "⏹️ DIHENTIKAN",
                    "keterangan": "Dihentikan oleh pengguna",
                    "worker_id": worker_id
                })
            return False
        self.event_bus.wait_if_paused()
        if self.event_bus.is_stop_requested():
            if row_idx and audit_data:
                audit_data["status"] = "DIHENTIKAN"
                audit_data["keterangan"] = "Dihentikan oleh pengguna"
                self.event_bus.emit("row_completed", {
                    "row_idx": row_idx,
                    "status": "⏹️ DIHENTIKAN",
                    "keterangan": "Dihentikan oleh pengguna",
                    "worker_id": worker_id
                })
            return False
        return True

    def _handle_relogin_needed(self, page, context, row_idx=None, keg_utama=None, is_midrun=False, worker_id=1):
        """Menangani kondisi sesi Fasih SSO kedaluwarsa atau belum login."""
        worker_tag = f"[W-{worker_id}] " if worker_id else ""
        with self.reauth_lock:
            if is_midrun:
                try:
                    if page and not page.is_closed() and BrowserManager.is_page_logged_in(page) and not BrowserManager.is_session_expired(page):
                        logger.info(f"{worker_tag}Sesi Fasih SSO telah dipulihkan oleh worker lain. Melanjutkan...")
                        return page
                except Exception:
                    pass

            # Opsi 1: Coba Auto-Login SSO BPS jika mode 'auto' dipilih pengguna
            if self.auth_mode == "auto" and self.sso_username and self.sso_password:
                logger.bot(f"{worker_tag}Sesi belum aktif / kedaluwarsa. Menjalankan Auto-Login SSO BPS (User: {self.sso_username})...")
                login_page = page
                if not login_page or login_page.is_closed():
                    if context.pages:
                        login_page = context.pages[0]
                    else:
                        login_page = context.new_page()

                auto_ok, auto_err = BrowserManager.perform_auto_login(
                    login_page, self.sso_username, self.sso_password
                )
                if auto_ok:
                    logger.success(f"🟢 {worker_tag}Auto-Login SSO BPS berhasil! Sesi telah aktif.")
                    if self.auto_minimize:
                        WindowController.minimize_browser()
                    time.sleep(1.5)
                    return login_page
                else:
                    logger.warning(f"⚠️ {worker_tag}Auto-Login gagal ({auto_err}). Beralih ke mode Login Manual...")

            # Opsi 2 / Fallback: Mode Login Manual (meminta pengguna login di Google Chrome)

            if is_midrun and row_idx:
                prefix = f"Baris {row_idx} [{keg_utama}]"
                msg = f"{worker_tag}Sesi Fasih kedaluwarsa di tengah jalan saat memproses {prefix}. Silakan login kembali di Google Chrome, lalu klik '🟢 Saya Sudah Login'."
                logger.warning(f"⚠️ {worker_tag}{prefix}: Sesi Fasih SSO kedaluwarsa di tengah jalan! Menjeda seluruh worker & menampilkan Google Chrome...")
            else:
                prefix = "Pemeriksaan Sesi Awal"
                msg = "Sesi Fasih SSO belum terdeteksi. Silakan login SSO BPS & OTP di Google Chrome, lalu klik '🟢 Saya Sudah Login'."
                logger.warning(f"⚠️ {prefix}: Sesi Fasih SSO belum aktif. Menampilkan jendela Google Chrome...")

            WindowController.restore_and_focus_browser()
            self.event_bus.reset_auth_confirmation()

            self.event_bus.emit("auth_waiting", {"message": msg, "is_midrun": is_midrun, "row_idx": row_idx, "worker_id": worker_id})
            logger.info(f"{worker_tag}Menunggu Anda login SSO BPS di Google Chrome ({'Mid-Run Baris ' + str(row_idx) if is_midrun else 'Awal'})...")

            active_page = page
            while True:
                if self.event_bus.is_stop_requested():
                    logger.warning(f"{worker_tag}Otomasi dihentikan oleh pengguna saat menunggu login SSO.")
                    return None

                if self.event_bus.is_auth_confirmed():
                    logger.success(f"🟢 {worker_tag}Konfirmasi login diterima dari pengguna! Memeriksa tab browser...")
                    detected = BrowserManager.find_authenticated_page(context)
                    if detected:
                        active_page = detected
                    elif not active_page or active_page.is_closed():
                        active_page = context.pages[0] if context.pages else None
                    break

                try:
                    if active_page and not active_page.is_closed():
                        if BrowserManager.is_page_logged_in(active_page) and not BrowserManager.is_session_expired(active_page):
                            logger.success(f"✅ {worker_tag}Login SSO Fasih berhasil dideteksi otomatis pada tab aktif!")
                            break
                except Exception:
                    pass

                detected = BrowserManager.find_authenticated_page(context)
                if detected:
                    active_page = detected
                    logger.success(f"✅ {worker_tag}Login SSO Fasih berhasil dideteksi otomatis pada tab browser!")
                    break

                time.sleep(0.5)

            if self.event_bus.is_stop_requested():
                return None

            self.event_bus.reset_auth_confirmation()

            if not active_page or active_page.is_closed():
                active_page = BrowserManager.find_authenticated_page(context)
                if not active_page and context.pages:
                    active_page = context.pages[0]

            try:
                active_page.wait_for_load_state("domcontentloaded", timeout=6000)
            except Exception:
                pass
            time.sleep(2.0)

            logger.success(f"🟢 {worker_tag}Sesi Fasih aktif! Melanjutkan proses otomasi...")
            self.event_bus.emit("auth_success", {"is_midrun": is_midrun, "row_idx": row_idx, "worker_id": worker_id})

            if self.auto_minimize:
                WindowController.minimize_browser()

            return active_page

    def _navigate_assignment_page(self, page, raw_url, row_idx=None, keg_utama="", worker_prefix=""):
        """Membuka URL penugasan dengan proteksi terhadap interupsi navigasi."""
        max_attempts = 4
        last_err = None
        for attempt in range(max_attempts):
            try:
                if page.is_closed():
                    raise Exception("Tab browser tertutup sebelum navigasi URL.")

                try:
                    page.wait_for_load_state("domcontentloaded", timeout=4000)
                except Exception:
                    pass

                page.goto(raw_url, timeout=45000, wait_until="domcontentloaded")
                random_sleep(1.2, 2.0, event_bus=self.event_bus)
                return True
            except Exception as nav_e:
                last_err = nav_e
                nav_err_msg = str(nav_e).lower()
                if any(k in nav_err_msg for k in ["interrupted", "navigation", "abort", "failed to navigate"]):
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"{worker_prefix}Navigasi baris {row_idx} terinterupsi ({nav_e}). "
                            f"Mencoba ulang ({attempt + 1}/{max_attempts})..."
                        )
                        time.sleep(2.5)
                        continue
                if attempt < max_attempts - 1:
                    time.sleep(1.5)
                else:
                    raise last_err
        return False

    def _process_single_assignment(self, worker_id, page, context, row_idx, wb, sheet, col_map, end_r, target_total):
        """Memproses satu baris penugasan KBLI Air 11502 secara mandiri per worker."""
        w_tag = f"[W-{worker_id}] "

        url_col = col_map.get("url")
        keg_col = col_map.get("keg_utama")
        kbli_lama_col = col_map.get("kbli_akhir")
        st_kbli_col = col_map.get("status_kbli")
        kbli_baru_col = col_map.get("kbli_terbaru")
        status_col = col_map.get("status")
        ket_col = col_map.get("keterangan")

        with self.excel_lock:
            url_val = sheet.cell(row=row_idx, column=url_col).value if url_col else None
            keg_utama = str(sheet.cell(row=row_idx, column=keg_col).value or "").strip() if keg_col else ""
            kbli_lama = str(sheet.cell(row=row_idx, column=kbli_lama_col).value or "").strip() if kbli_lama_col else ""
            st_kbli = str(sheet.cell(row=row_idx, column=st_kbli_col).value or "").strip() if st_kbli_col else ""
            kbli_baru = str(sheet.cell(row=row_idx, column=kbli_baru_col).value or "").strip() if kbli_baru_col else ""
            status_val = str(sheet.cell(row=row_idx, column=status_col).value or "").strip() if status_col else ""

        if not url_val or str(url_val).strip() == "":
            return

        with self.stats_lock:
            self.processed_count += 1
            curr_proc = self.processed_count

        # Emit progress update
        self.event_bus.emit("progress_updated", {
            "current": curr_proc,
            "total": target_total,
            "row_idx": row_idx,
            "keg_utama": keg_utama,
            "kbli_akhir": kbli_lama,
            "worker_id": worker_id
        })

        if status_val.upper() in ["SUKSES", "DONE", "SELESAI"]:
            with self.excel_lock:
                existing_ket = str(sheet.cell(row=row_idx, column=ket_col).value or "").strip() if ket_col else ""
            logger.info(f"{w_tag}Baris {row_idx} [{keg_utama[:25]}] berstatus {status_val} -> Dilewati.")
            with self.stats_lock:
                self.skipped_count += 1
            self.event_bus.emit("row_completed", {
                "row_idx": row_idx,
                "status": f"{status_val} (LEWAT)",
                "keterangan": existing_ket,
                "worker_id": worker_id
            })
            return

        # Update visual title tab Chrome
        try:
            file_label = Path(self.excel_path).stem[:10] if self.excel_path else "AIR11502"
            page.evaluate(f"() => {{ document.title = '[{file_label}|W-{worker_id}] {keg_utama[:16]}'; }}")
        except Exception:
            pass

        self.event_bus.emit("worker_status_updated", {
            "worker_id": worker_id,
            "status": "BUSY",
            "row_idx": row_idx,
            "nama_usaha": keg_utama
        })

        logger.bot(f"{w_tag}--- [Baris {row_idx}/{end_r}] Memproses KBLI: {keg_utama[:35]} (KBLI Lama: {kbli_lama} -> Baru: {kbli_baru}) ---")
        self.event_bus.emit("row_started", {
            "row_idx": row_idx,
            "keg_utama": keg_utama,
            "kbli_akhir": kbli_lama,
            "status_kbli": st_kbli,
            "kbli_terbaru": kbli_baru,
            "worker_id": worker_id
        })

        audit_data = {
            "row_index": row_idx,
            "keg_utama": keg_utama,
            "kbli_akhir": kbli_lama,
            "status_kbli": st_kbli,
            "kbli_terbaru": kbli_baru,
            "link_fasih": str(url_val).strip(),
            "status": "GAGAL"
        }

        try:
            raw_url = str(url_val).strip()
            if not raw_url.startswith(("http://", "https://")):
                raw_url = "https://" + raw_url

            max_reauth_attempts = 2
            reauth_count = 0

            while reauth_count <= max_reauth_attempts:
                try:
                    # Navigasi ke URL penugasan Fasih
                    self._navigate_assignment_page(page, raw_url, row_idx=row_idx, keg_utama=keg_utama, worker_prefix=w_tag)

                    if BrowserManager.is_session_expired(page) or not BrowserManager.is_page_logged_in(page):
                        raise SessionExpiredException("Sesi login Fasih tidak aktif atau kedaluwarsa.")

                    if not self.check_pause_and_stop(row_idx, audit_data, worker_id):
                        return

                    # STEP 1, 2, & 3: Buka Blok II & Temukan Usaha yang Sesuai keg_utama
                    def _chk_stop():
                        return self.check_pause_and_stop(row_idx, audit_data, worker_id)

                    found_match, matched_nama_usaha, err_match = _find_and_open_matching_business(
                        page, excel_keg_utama=keg_utama, event_bus=self.event_bus,
                        worker_prefix=w_tag, check_stop_fn=_chk_stop
                    )

                    if self.event_bus.is_stop_requested():
                        return

                    if not found_match:
                        skip_msg = err_match or f"Tidak ditemukan usaha di Blok II yang cocok dengan kegiatan utama '{keg_utama[:25]}'"
                        logger.warning(f"⚠️ {w_tag}Baris {row_idx}: {skip_msg} -> Dilewati.")
                        with self.excel_lock:
                            sheet.cell(row=row_idx, column=status_col).value = "DILEWATI"
                            sheet.cell(row=row_idx, column=ket_col).value = skip_msg
                            try:
                                wb.save(self.excel_path)
                            except Exception:
                                pass
                        with self.stats_lock:
                            self.skipped_count += 1
                        audit_data["status"] = "DILEWATI"
                        audit_data["keterangan"] = skip_msg
                        audit_logger.record_row(audit_data)
                        self.event_bus.emit("row_completed", {
                            "row_idx": row_idx,
                            "status": "⏭️ DILEWATI",
                            "keterangan": skip_msg,
                            "worker_id": worker_id
                        })
                        return

                    if not self.check_pause_and_stop(row_idx, audit_data, worker_id):
                        return

                    if matched_nama_usaha:
                        audit_data["nama_usaha"] = matched_nama_usaha

                    # STEP 3b: Pengisian Karakteristik Usaha KBLI Air 11502
                    logger.bot(f"{w_tag}Memproses karakteristik usaha KBLI Air 11502...")
                    char_ok, char_st, char_ket = _process_air_11502_characteristics(
                        page, event_bus=self.event_bus, worker_prefix=w_tag
                    )

                    if not char_ok:
                        logger.warning(f"⚠️ {w_tag}Baris {row_idx}: {char_ket} -> Dilewati.")
                        with self.excel_lock:
                            sheet.cell(row=row_idx, column=status_col).value = char_st
                            sheet.cell(row=row_idx, column=ket_col).value = char_ket
                            try:
                                wb.save(self.excel_path)
                            except Exception:
                                pass
                        with self.stats_lock:
                            self.skipped_count += 1
                        audit_data["status"] = char_st
                        audit_data["keterangan"] = char_ket
                        audit_logger.record_row(audit_data)
                        self.event_bus.emit("row_completed", {
                            "row_idx": row_idx,
                            "status": f"⏭️ {char_st}",
                            "keterangan": char_ket,
                            "worker_id": worker_id
                        })
                        return

                    if not self.check_pause_and_stop(row_idx, audit_data, worker_id):
                        return

                    # STEP 4: Verifikasi & Aksi KBLI (Kondisi 1 vs Kondisi 2)
                    logger.bot(f"{w_tag}Memeriksa rincian KBLI GenAI dan Master KBLI...")
                    kbli_ok, kbli_st, kbli_ket = _process_kbli_verification(
                        page, kbli_lama=kbli_lama, st_kbli=st_kbli, kbli_baru=kbli_baru,
                        event_bus=self.event_bus, worker_prefix=w_tag
                    )

                    if not kbli_ok:
                        logger.warning(f"⚠️ {w_tag}Baris {row_idx}: {kbli_ket} -> Dilewati.")
                        with self.excel_lock:
                            sheet.cell(row=row_idx, column=status_col).value = kbli_st
                            sheet.cell(row=row_idx, column=ket_col).value = kbli_ket
                            try:
                                wb.save(self.excel_path)
                            except Exception:
                                pass
                        with self.stats_lock:
                            self.skipped_count += 1
                        audit_data["status"] = kbli_st
                        audit_data["keterangan"] = kbli_ket
                        audit_logger.record_row(audit_data)
                        self.event_bus.emit("row_completed", {
                            "row_idx": row_idx,
                            "status": f"⏭️ {kbli_st}",
                            "keterangan": kbli_ket,
                            "worker_id": worker_id
                        })
                        return

                    if not self.check_pause_and_stop(row_idx, audit_data, worker_id):
                        return

                    # STEP 5: Submit Formulir Fasih
                    logger.bot(f"{w_tag}Menjalankan alur submit formulir Fasih...")
                    sub_ok, sub_st, sub_ket = _submit_assignment_form(
                        page, event_bus=self.event_bus, worker_prefix=w_tag,
                        debug_review=self.debug_review_submit, auto_minimize=self.auto_minimize,
                        row_idx=row_idx, keg_utama=keg_utama
                    )

                    if not sub_ok:
                        with self.excel_lock:
                            sheet.cell(row=row_idx, column=status_col).value = sub_st
                            sheet.cell(row=row_idx, column=ket_col).value = sub_ket
                            try:
                                wb.save(self.excel_path)
                            except Exception:
                                pass
                        with self.stats_lock:
                            self.error_count += 1
                        audit_data["status"] = sub_st
                        audit_data["keterangan"] = sub_ket
                        audit_logger.record_row(audit_data)
                        self.event_bus.emit("row_completed", {
                            "row_idx": row_idx,
                            "status": f"❌ {sub_st}",
                            "keterangan": sub_ket,
                            "worker_id": worker_id
                        })
                        return

                    # Checkpoint Sukses Akhir
                    prefix_usaha = f"[{matched_nama_usaha}] " if matched_nama_usaha else ""
                    final_ket = f"{prefix_usaha}{char_ket} | {kbli_ket} | {sub_ket}"
                    with self.excel_lock:
                        sheet.cell(row=row_idx, column=status_col).value = "SUKSES"
                        sheet.cell(row=row_idx, column=ket_col).value = final_ket
                        try:
                            wb.save(self.excel_path)
                        except Exception as save_err:
                            logger.warning(f"{w_tag}Gagal menyimpan checkpoint ke Excel: {save_err}")

                    with self.stats_lock:
                        self.done_session += 1

                    audit_data["status"] = "SUKSES"
                    audit_data["keterangan"] = final_ket
                    audit_logger.record_row(audit_data)

                    self.event_bus.emit("row_completed", {
                        "row_idx": row_idx,
                        "status": "✅ SUKSES",
                        "keterangan": final_ket,
                        "worker_id": worker_id
                    })
                    logger.success(f"{w_tag}✅ Baris {row_idx} [{keg_utama[:25]}] SELESAI (SUKSES).")
                    return

                except SessionExpiredException as sess_err:
                    reauth_count += 1
                    if reauth_count > max_reauth_attempts:
                        logger.error(f"❌ {w_tag}Baris {row_idx} [{keg_utama[:25]}]: Batas maksimum re-login ({max_reauth_attempts}x) tercapai.")
                        raise Exception(f"Sesi Fasih berulang kali kedaluwarsa pada baris ini ({sess_err})")

                    logger.warning(f"⚠️ {w_tag}Baris {row_idx} [{keg_utama[:25]}]: Sesi Fasih SSO kedaluwarsa di tengah jalan! Menjeda & menampilkan Google Chrome...")
                    self.event_bus.request_pause()
                    page = self._handle_relogin_needed(page, context, row_idx=row_idx, keg_utama=keg_utama, is_midrun=True, worker_id=worker_id)
                    self.event_bus.request_resume()

                    if not page or self.event_bus.is_stop_requested():
                        audit_data["status"] = "DIHENTIKAN"
                        audit_data["keterangan"] = "Dihentikan oleh pengguna saat sesi login kedaluwarsa"
                        self.event_bus.emit("row_completed", {
                            "row_idx": row_idx,
                            "status": "⏹️ DIHENTIKAN",
                            "keterangan": "Dihentikan oleh pengguna saat sesi login kedaluwarsa",
                            "worker_id": worker_id
                        })
                        return

                    logger.info(f"🔄 {w_tag}Mengulang kembali proses otomasi Baris {row_idx} [{keg_utama[:25]}] dari awal (Percobaan ke-{reauth_count + 1})...")
                    time.sleep(2.0)
                    continue

                except Exception as step_err:
                    if (BrowserManager.is_session_expired(page) or not BrowserManager.is_page_logged_in(page)) and reauth_count < max_reauth_attempts:
                        reauth_count += 1
                        logger.warning(f"⚠️ {w_tag}Baris {row_idx} [{keg_utama[:25]}]: Sesi Fasih terputus di tengah proses ({step_err}). Menjeda & menampilkan Google Chrome...")
                        self.event_bus.request_pause()
                        page = self._handle_relogin_needed(page, context, row_idx=row_idx, keg_utama=keg_utama, is_midrun=True, worker_id=worker_id)
                        self.event_bus.request_resume()

                        if not page or self.event_bus.is_stop_requested():
                            audit_data["status"] = "DIHENTIKAN"
                            audit_data["keterangan"] = "Dihentikan oleh pengguna saat sesi login kedaluwarsa"
                            self.event_bus.emit("row_completed", {
                                "row_idx": row_idx,
                                "status": "⏹️ DIHENTIKAN",
                                "keterangan": "Dihentikan oleh pengguna saat sesi login kedaluwarsa",
                                "worker_id": worker_id
                            })
                            return

                        logger.info(f"🔄 {w_tag}Mengulang kembali proses otomasi Baris {row_idx} [{keg_utama[:25]}] dari awal (Percobaan ke-{reauth_count + 1})...")
                        time.sleep(2.0)
                        continue
                    else:
                        raise step_err

        except Exception as row_err:
            error_msg = str(row_err)
            logger.error(f"❌ {w_tag}Baris {row_idx} [{keg_utama[:25]}] GAGAL: {error_msg}")
            with self.excel_lock:
                sheet.cell(row=row_idx, column=status_col).value = "GAGAL"
                sheet.cell(row=row_idx, column=ket_col).value = error_msg[:150]
                try:
                    wb.save(self.excel_path)
                except Exception:
                    pass

            with self.stats_lock:
                self.error_count += 1

            audit_data["status"] = "GAGAL"
            audit_data["keterangan"] = error_msg
            audit_logger.record_row(audit_data)

            self.event_bus.emit("row_completed", {
                "row_idx": row_idx,
                "status": "❌ GAGAL",
                "keterangan": error_msg[:100],
                "worker_id": worker_id
            })

        finally:
            self.event_bus.emit("worker_status_updated", {
                "worker_id": worker_id,
                "status": "IDLE",
                "row_idx": None,
                "nama_usaha": ""
            })
            random_sleep(0.8, 1.5, event_bus=self.event_bus)

    def run(self):
        """Metode utama eksekusi engine KBLI Air 11502."""
        logger.info(f"Memulai Engine KBLI Air 11502 SE2026 (Konfigurasi Worker: {self.num_workers} Worker)...")
        self.event_bus.set_state(EngineState.RUNNING)

        wb = None

        # 1. Validasi awal template Excel
        val_res = ExcelKBLIAir11502Validator.validate_excel_file(self.excel_path)
        if not val_res["valid"]:
            logger.error(f"Validasi file Excel gagal: {val_res['error']}")
            self.event_bus.set_state(EngineState.IDLE)
            self.event_bus.emit("all_completed", {
                "done": 0, "error": 0, "skipped": 0, "was_stopped": False
            })
            return

        col_map = val_res["col_map"]

        try:
            wb = openpyxl.load_workbook(self.excel_path)
            sheet = wb.active
        except Exception as e:
            logger.error(f"Gagal memuat workbook Excel: {e}")
            self.event_bus.set_state(EngineState.IDLE)
            self.event_bus.emit("all_completed", {
                "done": 0, "error": 0, "skipped": 0, "was_stopped": False
            })
            return

        # 2. Hubungkan ke Browser CDP (atau luncurkan otomatis jika belum aktif)
        cdp_port = BrowserManager.get_cdp_port(self.browser_type)
        b_label = "Microsoft Edge" if self.browser_type == "edge" else "Google Chrome"
        is_running, b_name = BrowserManager.is_cdp_running(browser_type=self.browser_type, port=cdp_port)
        if not is_running:
            logger.info(f"Browser ({b_label}) belum aktif di port {cdp_port}. Meluncurkan {b_label} secara otomatis...")
            launched, launch_msg = BrowserManager.launch_browser(browser_type=self.browser_type, incognito=self.incognito)
            if not launched:
                logger.error(f"Gagal meluncurkan browser: {launch_msg}")
                self.event_bus.set_state(EngineState.IDLE)
                self.event_bus.emit("all_completed", {
                    "done": 0, "error": 0, "skipped": 0, "was_stopped": False
                })
                wb.close()
                return
            time.sleep(1.5)

        # 3. Probe SSO Awal
        logger.info("Memeriksa status otentikasi SSO Fasih awal...")
        try:
            with sync_playwright() as p_probe:
                browser_probe = p_probe.chromium.connect_over_cdp(self.cdp_url)
                context_probe = browser_probe.contexts[0]
                page_probe = BrowserManager.find_authenticated_page(context_probe)
                if not page_probe:
                    for p_cand in context_probe.pages:
                        if "fasih-sm.bps.go.id" in p_cand.url:
                            page_probe = p_cand
                            break
                    if not page_probe:
                        page_probe = context_probe.pages[0] if context_probe.pages else context_probe.new_page()
                        if "fasih-sm.bps.go.id" not in page_probe.url:
                            try:
                                page_probe.goto("https://fasih-sm.bps.go.id/app", timeout=30000)
                            except Exception:
                                pass

                if not BrowserManager.is_page_logged_in(page_probe) or BrowserManager.is_session_expired(page_probe):
                    page_probe = self._handle_relogin_needed(page_probe, context_probe, is_midrun=False, worker_id=1)
                    if not page_probe or self.event_bus.is_stop_requested():
                        logger.warning("Otomasi dibatalkan sebelum login SSO selesai.")
                        wb.close()
                        self.event_bus.set_state(EngineState.IDLE)
                        self.event_bus.emit("all_completed", {
                            "done": 0, "error": 0, "skipped": 0, "was_stopped": True
                        })
                        return
                elif self.auto_minimize:
                    WindowController.minimize_browser()
        except Exception as e_probe:
            logger.error(f"Gagal memeriksa status SSO Fasih: {e_probe}")
            wb.close()
            self.event_bus.set_state(EngineState.IDLE)
            self.event_bus.emit("all_completed", {
                "done": 0, "error": 0, "skipped": 0, "was_stopped": False
            })
            return

        # 4. Kolom mapping & persiapan checkpoint
        url_col = col_map.get("url")
        status_col = col_map.get("status")
        ket_col = col_map.get("keterangan")

        with self.excel_lock:
            if not status_col:
                status_col = sheet.max_column + 1
                col_map["status"] = status_col
                sheet.cell(row=1, column=status_col).value = "Status_Eksekusi"
                logger.info(f"Kolom 'Status_Eksekusi' otomatis dibuat di kolom {status_col}.")
            if not ket_col:
                ket_col = sheet.max_column + 1
                col_map["keterangan"] = ket_col
                sheet.cell(row=1, column=ket_col).value = "Keterangan"
                logger.info(f"Kolom 'Keterangan' otomatis dibuat di kolom {ket_col}.")

        max_row = sheet.max_row
        start_r = max(2, self.row_start)
        end_r = min(max_row, self.row_end) if self.row_end else max_row

        target_rows = [
            r for r in range(start_r, end_r + 1)
            if url_col and sheet.cell(row=r, column=url_col).value and str(sheet.cell(row=r, column=url_col).value).strip() != ""
        ]
        target_total = len(target_rows) if target_rows else max(1, end_r - start_r + 1)

        if not target_rows:
            logger.warning("Tidak ditemukan baris penugasan yang valid dalam rentang yang dipilih.")
            wb.close()
            self.event_bus.set_state(EngineState.IDLE)
            self.event_bus.emit("all_completed", {
                "done": 0, "error": 0, "skipped": 0, "was_stopped": False
            })
            return

        actual_workers = min(self.num_workers, len(target_rows))
        logger.info(f"Rentang baris target: {start_r} s.d. {end_r} (Ditemukan {len(target_rows)} baris penugasan). Mengaktifkan {actual_workers} Worker.")

        for r_idx in target_rows:
            self.task_queue.put(r_idx)

        # Worker runner loop
        def worker_runner(w_id):
            w_tag = f"[W-{w_id}] "
            try:
                with sync_playwright() as p_worker:
                    browser = p_worker.chromium.connect_over_cdp(self.cdp_url)
                    context = browser.contexts[0]

                    file_label = Path(self.excel_path).stem[:10] if self.excel_path else "AIR11502"

                    # Alokasi halaman tab baru terisolasi
                    page = context.new_page()

                    try:
                        page.evaluate(f"() => {{ document.title = '[{file_label}|W-{w_id}] Fasih KBLI Helper'; }}")
                    except Exception:
                        pass

                    self.event_bus.emit("worker_status_updated", {
                        "worker_id": w_id, "status": "IDLE", "row_idx": None, "nama_usaha": ""
                    })
                    logger.info(f"{w_tag}Tab worker KBLI siap beroperasi.")

                    while not self.event_bus.is_stop_requested():
                        self.event_bus.wait_if_paused()
                        if self.event_bus.is_stop_requested():
                            break

                        try:
                            row_idx = self.task_queue.get_nowait()
                        except queue.Empty:
                            break

                        # Self-healing tab check
                        try:
                            if page.is_closed():
                                logger.warning(f"{w_tag}Tab terdeteksi tertutup! Membuka kembali tab baru secara otomatis...")
                                page = context.new_page()
                                try:
                                    page.evaluate(f"() => {{ document.title = '[{file_label}|W-{w_id}] Fasih KBLI Helper'; }}")
                                except Exception:
                                    pass
                        except Exception as e_reopen:
                            logger.error(f"{w_tag}Gagal memulihkan tab: {e_reopen}")
                            self.task_queue.task_done()
                            break

                        try:
                            self._process_single_assignment(
                                worker_id=w_id,
                                page=page,
                                context=context,
                                row_idx=row_idx,
                                wb=wb,
                                sheet=sheet,
                                col_map=col_map,
                                end_r=end_r,
                                target_total=target_total
                            )
                        except Exception as e_row:
                            logger.error(f"{w_tag}Error tak terduga pada baris {row_idx}: {e_row}")
                        finally:
                            self.task_queue.task_done()

                    # Bersihkan tab saat worker selesai
                    try:
                        page.close()
                    except Exception:
                        pass

                    self.event_bus.emit("worker_status_updated", {
                        "worker_id": w_id, "status": "DONE", "row_idx": None, "nama_usaha": ""
                    })
                    logger.info(f"{w_tag}Worker selesai.")

            except Exception as e_worker:
                logger.error(f"{w_tag}Worker mengalami gangguan koneksi CDP: {e_worker}")
                self.event_bus.emit("worker_status_updated", {
                    "worker_id": w_id, "status": "ERROR", "row_idx": None, "nama_usaha": ""
                })

        try:
            threads = []
            for w_id in range(1, actual_workers + 1):
                t = threading.Thread(target=worker_runner, args=(w_id,), name=f"KBLIAir11502Worker-{w_id}")
                t.start()
                threads.append(t)
                time.sleep(0.4)

            # Tunggu semua worker selesai
            for t in threads:
                t.join()

        finally:
            if wb:
                try:
                    with self.excel_lock:
                        wb.save(self.excel_path)
                        wb.close()
                except Exception:
                    pass

            if self.auto_minimize:
                try:
                    WindowController.restore_and_focus_browser()
                except Exception:
                    pass

            was_stopped = self.event_bus.is_stop_requested()
            self.event_bus.set_state(EngineState.IDLE)
            if was_stopped:
                logger.warning(f"⏹️ Otomasi Dihentikan oleh Pengguna! (Sukses Sesi Ini: {self.done_session}, Gagal: {self.error_count}, Dilewati: {self.skipped_count})")
            else:
                logger.success(f"🏁 Eksekusi KBLI Air 11502 Selesai! (Sukses Sesi Ini: {self.done_session}, Gagal: {self.error_count}, Dilewati: {self.skipped_count})")

            self.event_bus.emit("all_completed", {
                "done": self.done_session,
                "error": self.error_count,
                "skipped": self.skipped_count,
                "was_stopped": was_stopped
            })

# Alias untuk kompatibilitas
KBLIAir11052Engine = KBLIAir11502Engine

