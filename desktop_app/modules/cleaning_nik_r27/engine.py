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
from modules.cleaning_nik_r27.selectors import EXCEL_NIK_R27_COLUMNS_CONFIG, NIK_R27_SELECTORS
from modules.cleaning_nik_r27.validator import ExcelNIKR27Validator

def human_jitter(min_sec=0.1, max_sec=0.3, event_bus=None):
    """Jeda acak mikro untuk mensimulasikan interaksi manusia."""
    if event_bus and event_bus.is_stop_requested():
        return
    t = random.uniform(min_sec, max_sec)
    time.sleep(t)

def random_sleep(min_sec=0.5, max_sec=1.5, event_bus=None, allow_hesitation=True):
    """Jeda acak antar aksi tombol/navigasi."""
    if event_bus and event_bus.is_stop_requested():
        return
    base = random.uniform(min_sec, max_sec)
    if allow_hesitation and random.random() < 0.15:
        base += random.uniform(0.5, 1.2)
    time.sleep(base)

def safe_click(page, selector_or_locator, timeout=20000, event_bus=None, force=False):
    """Melakukan scroll, jitter, lalu klik secara aman pada elemen."""
    if event_bus and event_bus.is_stop_requested():
        return
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

def clean_nik_str(val):
    """Membersihkan nilai NIK agar murni angka digit (menghilangkan spasi, titik, strip, .0)."""
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return re.sub(r"[^\d]", "", s)

def add_remarks_to_element(page, container_locator_or_sel, note_text="#0", event_bus=None, worker_prefix=""):
    """
    Membuka modal Catatan pada elemen container NIK, mengetik catatan '#0', klik simpan, lalu tutup modal.
    Idempotent: Jika catatan sudah ada di bubble chat, lewati pengiriman ulang.
    """
    if isinstance(container_locator_or_sel, str):
        container = page.locator(container_locator_or_sel).first
    else:
        container = container_locator_or_sel
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
        if not btn_catatan and all_btns.count() > 0:
            btn_catatan = all_btns.first

    if not btn_catatan:
        raise Exception("Tombol Catatan visible tidak ditemukan pada container NIK")

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
        logger.info(f"{worker_prefix}Catatan '{note_str}' sudah tercatat sebelumnya. Melewati penulisan ulang.")
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

def ensure_anomali_switch_active(page, event_bus=None, wait_timeout=35000, worker_prefix=""):
    """
    Pastikan switch 'Tampilkan Anomali Usaha dan Keluarga' (div#cek_anomali_button) AKTIF di Blok Catatan.
    """
    box = page.locator("div#cek_anomali_button").first
    try:
        box.wait_for(state="visible", timeout=wait_timeout)
    except PlaywrightTimeoutError:
        raise Exception("Switch 'Tampilkan Anomali Usaha dan Keluarga' tidak muncul di Blok Catatan.")

    try:
        box.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    sw_input = box.locator("input[role='switch']").first
    sw_control = box.locator("[id^='switch-'][id$='-control']").first

    def _is_active():
        return sw_input.get_attribute("aria-checked") == "true"

    if _is_active():
        logger.bot(f"{worker_prefix}Switch 'Tampilkan Anomali Usaha dan Keluarga' sudah aktif -> Dibiarkan.")
        return False

    logger.bot(f"{worker_prefix}Switch 'Tampilkan Anomali Usaha dan Keluarga' belum aktif -> Mengaktifkan...")
    for attempt in range(1, 4):
        safe_click(page, sw_control, timeout=5000, event_bus=event_bus)
        for _ in range(10):
            random_sleep(0.25, 0.35, event_bus=event_bus, allow_hesitation=False)
            if _is_active():
                logger.bot(f"{worker_prefix}Switch 'Tampilkan Anomali Usaha dan Keluarga' berhasil diaktifkan.")
                return True
        logger.warning(f"{worker_prefix}Switch anomali belum aktif setelah klik (percobaan {attempt}/3). Mengulang...")

    raise Exception("Gagal mengaktifkan toggle Tampilkan Anomali Usaha dan Keluarga.")

def _get_valid_art_items(page):
    """
    Mengambil daftar item anggota keluarga (ART) yang valid dan clickable dari sub-sidebar Blok I.
    Mengembalikan list of tuple: (locator, clean_nama_art)
    """
    sel = (
        "xpath=//div[@title='Keterangan Anggota Keluarga']/following-sibling::div[@data-expanded]"
        "//div[contains(@class, 'fasih-form-sidebar')]/div[contains(@class, 'cursor-pointer') and @title]"
    )
    subs = page.locator(sel)
    cnt = subs.count()
    if cnt == 0:
        sel_fallback = (
            "xpath=//div[@title='Keterangan Anggota Keluarga']/following-sibling::div"
            "//div[contains(@class, 'fasih-form-sidebar')]/div[contains(@class, 'cursor-pointer') and @title]"
        )
        subs = page.locator(sel_fallback)
        cnt = subs.count()

    valid_items = []
    for idx in range(cnt):
        item_loc = subs.nth(idx)
        raw_title = (item_loc.get_attribute("title") or "").strip()
        if not raw_title:
            try:
                raw_title = item_loc.inner_text().strip()
            except Exception:
                pass
        clean_name = normalize_text(raw_title)
        if clean_name and "keterangan anggota keluarga" not in clean_name and "blok i" not in clean_name:
            valid_items.append((item_loc, raw_title))

    return valid_items

def _submit_assignment_form(page, event_bus, row_idx, debug_review=False, auto_minimize=True, worker_prefix=""):
    """
    Menjalankan alur submit formulir penugasan:
    1. Buka Blok Catatan
    2. Pastikan switch toggle anomali aktif
    3. Klik Kirim pada formulir Fasih (btn-kirim)
    4. Tunggu pop-up validasi Kirim -> Periksa Galat (batal jika > 0) -> Klik Kirim pada modal validasi
    5. Tunggu dialog Konfirmasi Kirim ("Apakah Anda yakin...") -> Konfirmasi (dengan jeda Mode Review Debugging)
    6. Verifikasi respon sukses
    """
    # 1. Buka Blok Catatan
    logger.bot(f"{worker_prefix}Membuka menu Blok Catatan...")
    try:
        catatan_menu = page.locator(NIK_R27_SELECTORS["sidebar_blok_catatan"]).first
        catatan_menu.wait_for(state="visible", timeout=20000)
        safe_click(page, catatan_menu, timeout=15000, event_bus=event_bus)
        random_sleep(1.0, 1.5, event_bus=event_bus)
    except Exception as e:
        logger.warning(f"{worker_prefix}Gagal klik menu Blok Catatan: {e}")

    # 2. Pastikan switch toggle anomali aktif di Blok Catatan
    ensure_anomali_switch_active(page, event_bus=event_bus, wait_timeout=35000, worker_prefix=worker_prefix)
    random_sleep(1.5, 2.2, event_bus=event_bus, allow_hesitation=False)

    # 3. Klik Kirim pada formulir Fasih
    logger.bot(f"{worker_prefix}[1/4] Mengklik tombol Kirim formulir Fasih...")
    form_kirim_btn = page.locator(NIK_R27_SELECTORS["btn_kirim"]).first
    form_kirim_btn.wait_for(state="attached", timeout=25000)
    safe_click(page, form_kirim_btn, timeout=25000, event_bus=event_bus, force=True)
    random_sleep(1.0, 1.8, event_bus=event_bus, allow_hesitation=False)

    # 4. Dialog Pop-up Validasi Kirim
    btn_konfirmasi = page.locator(NIK_R27_SELECTORS["btn_konfirmasi_kirim"]).last
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
            err_msg = f"Terdapat {galat_count} Galat pada formulir penugasan. Submit dibatalkan."
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

    # 5. Dialog Konfirmasi Kirim ("Apakah Anda yakin...")
    logger.bot(f"{worker_prefix}[3/4] Menunggu dialog Konfirmasi Kirim...")
    btn_konfirmasi = page.locator(NIK_R27_SELECTORS["btn_konfirmasi_kirim"]).last
    btn_konfirmasi.wait_for(state="visible", timeout=30000)
    random_sleep(0.5, 1.0, event_bus=event_bus, allow_hesitation=False)

    if debug_review:
        logger.warning(f"🔍 [MODE REVIEW DEBUGGING] {worker_prefix}Baris #{row_idx}: Modal Konfirmasi Kirim terbuka.")
        logger.info("Silakan periksa browser. Klik '✅ Konfirmasi Submit & Lanjut' di aplikasi atau tekan Enter untuk mengirimkan.")
        WindowController.restore_and_focus_browser()
        event_bus.emit("waiting_confirm_submit", {
            "row_idx": row_idx,
            "nama_usaha": f"Baris #{row_idx}",
            "worker_id": worker_prefix
        })
        event_bus.wait_for_submit_confirmation()
        if event_bus.is_stop_requested():
            return False, "DIHENTIKAN", "Dihentikan oleh pengguna saat review konfirmasi"
        logger.bot(f"{worker_prefix}Konfirmasi diterima. Melanjutkan klik Konfirmasi...")
        safe_click(page, btn_konfirmasi, timeout=20000, event_bus=event_bus, force=True)
        if auto_minimize:
            WindowController.minimize_browser()
    else:
        logger.bot(f"{worker_prefix}[3/4] Mengklik tombol Konfirmasi...")
        safe_click(page, btn_konfirmasi, timeout=20000, event_bus=event_bus, force=True)

    # 6. Menunggu dialog sukses
    logger.bot(f"{worker_prefix}[4/4] Menunggu respon submit Fasih...")
    try:
        success_dialog = page.locator(NIK_R27_SELECTORS["dialog_sukses"]).first
        success_dialog.wait_for(state="visible", timeout=40000)
        logger.success(f"{worker_prefix}Assignment penugasan berhasil disubmit.")
    except Exception:
        logger.warning(f"{worker_prefix}Dialog sukses tidak terdeteksi eksplisit, melanjutkan...")

    return True, "SUKSES", "Assignment berhasil disubmit"

# ==============================================================================
# ENGINE OTOMASI DATA CLEANING NIK R27 (MULTI-WORKER RUNNER)
# ==============================================================================

class SessionExpiredException(Exception):
    """Exception khusus saat sesi Fasih SSO kedaluwarsa atau belum terotentikasi di tengah jalan."""
    pass

class CleaningNIKR27Engine:
    def __init__(self, excel_path, event_bus, config_options=None):
        self.excel_path = excel_path
        self.event_bus = event_bus
        self.config_options = config_options or {}
        self.auto_minimize = self.config_options.get("auto_minimize", True)
        self.debug_review_submit = self.config_options.get("debug_review_submit", False)
        self.row_start = self.config_options.get("row_start", 2)
        self.row_end = self.config_options.get("row_end", None)

        # Konfigurasi Mode Login SSO
        self.auth_mode = self.config_options.get("auth_mode", "manual")
        self.sso_username = self.config_options.get("sso_username", "").strip()
        self.sso_password = self.config_options.get("sso_password", "").strip()

        # Konfigurasi Multi-Worker (1 s.d. 5 worker)
        raw_workers = self.config_options.get("num_workers", 2)
        try:
            self.num_workers = max(1, min(5, int(raw_workers)))
        except (ValueError, TypeError):
            self.num_workers = 2

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

    def _handle_relogin_needed(self, page, context, row_idx=None, is_midrun=False, worker_id=1):
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
                msg = f"{worker_tag}Sesi Fasih kedaluwarsa di tengah jalan saat memproses Baris #{row_idx}. Silakan login kembali di Google Chrome, lalu klik '🟢 Saya Sudah Login'."
                logger.warning(f"⚠️ {worker_tag}Baris #{row_idx}: Sesi Fasih SSO kedaluwarsa di tengah jalan! Menjeda seluruh worker & menampilkan Google Chrome...")
            else:
                msg = "Sesi Fasih SSO belum terdeteksi. Silakan login SSO BPS & OTP di Google Chrome, lalu klik '🟢 Saya Sudah Login'."
                logger.warning(f"⚠️ Pemeriksaan Sesi Awal: Sesi Fasih SSO belum aktif. Menampilkan jendela Google Chrome...")

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
            time.sleep(1.5)

            logger.success(f"🟢 {worker_tag}Sesi Fasih aktif! Melanjutkan proses otomasi...")
            self.event_bus.emit("auth_success", {"is_midrun": is_midrun, "row_idx": row_idx, "worker_id": worker_id})

            if self.auto_minimize:
                WindowController.minimize_browser()

            return active_page

    def _worker_loop(self, worker_id, task_queue):
        """Worker thread loop untuk mengeksekusi baris tugas secara paralel."""
        worker_tag = f"[W-{worker_id}] "
        logger.info(f"{worker_tag}Worker dimulai.")

        page = None
        try:
            with sync_playwright() as p_worker:
                try:
                    browser = p_worker.chromium.connect_over_cdp(CDP_URL)
                except Exception as e:
                    logger.error(f"❌ {worker_tag}Gagal menghubungkan ke browser Chrome (CDP Port 9222): {e}")
                    return

                context = browser.contexts[0] if browser.contexts else browser.new_context()

                try:
                    page = context.new_page()
                    page.set_default_timeout(35000)
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=4000)
                    except Exception:
                        pass
                except Exception as e:
                    logger.error(f"❌ {worker_tag}Gagal membuat tab browser: {e}")
                    return

                logger.info(f"{worker_tag}Tab worker NIK R27 siap beroperasi.")

                while not self.event_bus.is_stop_requested():
                    self.event_bus.wait_if_paused()
                    if self.event_bus.is_stop_requested():
                        break

                    try:
                        row_data = task_queue.get_nowait()
                    except queue.Empty:
                        break

                    row_idx = row_data["_row_num"]
                    url = row_data.get("url", "").strip()
                    total_nik = row_data.get("total_nik", 0)
                    target_niks = row_data.get("nik_list", [])

                    self.event_bus.emit("row_started", {
                        "row_idx": row_idx,
                        "url": url,
                        "worker_id": worker_id
                    })

                    logger.bot(f"{worker_tag}--- Memproses Baris Excel #{row_idx} (Target: {len(target_niks)} NIK) ---")

                    audit_data = {
                        "row_index": row_idx,
                        "url": url,
                        "target_niks": target_niks,
                        "total_nik": total_nik,
                        "timestamp_start": datetime.now().isoformat(),
                        "status": "PROSES",
                        "keterangan": "",
                        "worker_id": worker_id
                    }

                    try:
                        if not self.check_pause_and_stop(row_idx, audit_data, worker_id):
                            break

                        # 1. Validasi awal data baris Excel
                        if not url or not url.startswith("http"):
                            err_msg = "GAGAL: URL penugasan Fasih kosong atau tidak valid (harus diawali http/https)."
                            logger.warning(f"{worker_tag}{err_msg}")
                            self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                            continue

                        if not target_niks:
                            err_msg = f"GAGAL: Kolom target NIK kosong pada baris ini (total_nik tercatat: {total_nik})."
                            logger.warning(f"{worker_tag}{err_msg}")
                            self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                            continue

                        # Bersihkan target NIK: mapping clean_nik -> original_string
                        clean_targets = {}
                        for n in target_niks:
                            cn = clean_nik_str(n)
                            if cn:
                                clean_targets[cn] = n

                        # 2. Buka Halaman Penugasan Fasih SM
                        logger.bot(f"{worker_tag}Membuka URL: {url}")
                        try:
                            page.goto(url, timeout=45000, wait_until="domcontentloaded")
                            random_sleep(1.0, 1.8, event_bus=self.event_bus)
                        except Exception as e:
                            err_msg = f"GAGAL: Tidak dapat memuat tautan penugasan: {e}"
                            logger.error(f"{worker_tag}{err_msg}")
                            self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                            continue

                        # Periksa apakah sesi kedaluwarsa
                        if BrowserManager.is_session_expired(page) or not BrowserManager.is_page_logged_in(page):
                            page = self._handle_relogin_needed(page, context, row_idx=row_idx, is_midrun=True, worker_id=worker_id)
                            if not page or self.event_bus.is_stop_requested():
                                break
                            try:
                                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                                random_sleep(1.0, 1.5, event_bus=self.event_bus)
                            except Exception as e:
                                err_msg = f"GAGAL: Tidak dapat memuat URL setelah login ulang: {e}"
                                self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                                continue

                        # 3. Masuk ke Blok I (Keterangan Umum Keluarga)
                        logger.bot(f"{worker_tag}Membuka menu 'SE2026 - L BLOK I'...")
                        try:
                            blok_i_btn = page.locator(NIK_R27_SELECTORS["sidebar_blok_i"]).first
                            blok_i_btn.wait_for(state="visible", timeout=25000)
                            safe_click(page, blok_i_btn, timeout=20000, event_bus=self.event_bus)
                            random_sleep(0.8, 1.3, event_bus=self.event_bus)
                        except Exception as e:
                            if BrowserManager.is_session_expired(page) or not BrowserManager.is_page_logged_in(page):
                                logger.warning(f"⚠️ {worker_tag}Terdeteksi sesi terlempar ke login saat membuka formulir.")
                                page = self._handle_relogin_needed(page, context, row_idx=row_idx, is_midrun=True, worker_id=worker_id)
                                if not page or self.event_bus.is_stop_requested():
                                    break
                                try:
                                    page.goto(url, timeout=45000, wait_until="domcontentloaded")
                                    random_sleep(1.0, 1.5, event_bus=self.event_bus)
                                    blok_i_btn = page.locator(NIK_R27_SELECTORS["sidebar_blok_i"]).first
                                    blok_i_btn.wait_for(state="visible", timeout=25000)
                                    safe_click(page, blok_i_btn, timeout=20000, event_bus=self.event_bus)
                                    random_sleep(0.8, 1.3, event_bus=self.event_bus)
                                except Exception as ex2:
                                    err_msg = f"GAGAL: Menu 'SE2026 - L BLOK I' tidak ditemukan di formulir web: {ex2}"
                                    logger.error(f"{worker_tag}{err_msg}")
                                    self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                                    continue
                            else:
                                err_msg = f"GAGAL: Menu 'SE2026 - L BLOK I' tidak ditemukan di formulir web: {e}"
                                logger.error(f"{worker_tag}{err_msg}")
                                self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                                continue

                        # 4. Pastikan submenu 'Keterangan Anggota Keluarga' terbuka
                        try:
                            ket_art_header = page.locator(NIK_R27_SELECTORS["sidebar_ket_art"]).first
                            ket_art_header.wait_for(state="visible", timeout=20000)
                            # Cek apakah sudah expanded
                            expanded_wrapper = page.locator("xpath=//div[@title='Keterangan Anggota Keluarga']/following-sibling::div[@data-expanded]")
                            if expanded_wrapper.count() == 0 or not expanded_wrapper.first.is_visible():
                                logger.bot(f"{worker_tag}Membuka accordion 'Keterangan Anggota Keluarga'...")
                                safe_click(page, ket_art_header, timeout=15000, event_bus=self.event_bus)
                                random_sleep(0.8, 1.2, event_bus=self.event_bus)
                        except Exception as e:
                            err_msg = f"GAGAL: Submenu 'Keterangan Anggota Keluarga' tidak dapat dibuka: {e}"
                            logger.error(f"{worker_tag}{err_msg}")
                            self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                            continue

                        # 5. Dapatkan daftar anggota keluarga yang ada di web
                        art_items = _get_valid_art_items(page)
                        if not art_items:
                            err_msg = "GAGAL: Tidak ditemukan daftar anggota keluarga (ART) yang dapat diakses di sidebar formulir."
                            logger.error(f"{worker_tag}{err_msg}")
                            self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                            continue

                        logger.info(f"{worker_tag}Ditemukan {len(art_items)} anggota keluarga di web. Memulai pengecekan NIK...")

                        matched_niks = {}    # clean_nik -> nama_art
                        inspected_arts = []  # list of strings: nama_art (web_nik)
                        has_error = False
                        error_detail = ""

                        # 6. Iterasi setiap anggota keluarga di sidebar
                        for a_idx, (art_loc, art_title) in enumerate(art_items, start=1):
                            if not self.check_pause_and_stop(row_idx, audit_data, worker_id):
                                has_error = True
                                break

                            logger.bot(f"{worker_tag}[ART {a_idx}/{len(art_items)}] Membuka formulir ART '{art_title}'...")
                            try:
                                safe_click(page, art_loc, timeout=15000, event_bus=self.event_bus)
                                random_sleep(0.8, 1.4, event_bus=self.event_bus)
                            except Exception as e:
                                logger.warning(f"{worker_tag}Gagal mengklik ART '{art_title}': {e}. Melewati...")
                                inspected_arts.append(f"{art_title} (Gagal Klik)")
                                continue

                            # Cari container rincian 7. NIK (nik_dtsen)
                            nik_box = page.locator(NIK_R27_SELECTORS["container_nik"]).first
                            try:
                                nik_box.wait_for(state="attached", timeout=15000)
                                nik_box.scroll_into_view_if_needed(timeout=4000)
                            except Exception:
                                logger.warning(f"{worker_tag}Container rincian NIK (div#nik_dtsen) tidak ditemukan pada ART '{art_title}'.")
                                inspected_arts.append(f"{art_title} (Tanpa Input NIK)")
                                continue

                            inp_nik = nik_box.locator(NIK_R27_SELECTORS["input_nik"]).first
                            web_nik_raw = ""
                            try:
                                web_nik_raw = inp_nik.input_value().strip()
                            except Exception:
                                pass
                            if not web_nik_raw:
                                web_nik_raw = (inp_nik.get_attribute("value") or "").strip()

                            web_nik_clean = clean_nik_str(web_nik_raw)
                            inspected_arts.append(f"{art_title}: {web_nik_clean or 'KOSONG'}")

                            logger.bot(f"{worker_tag}ART '{art_title}' -> NIK Web: '{web_nik_raw}' (Clean: {web_nik_clean})")

                            # Cek apakah NIK ini merupakan target yang perlu diremark
                            if web_nik_clean in clean_targets:
                                orig_target = clean_targets[web_nik_clean]
                                logger.success(f"{worker_tag}✨ NIK COCOK! ART '{art_title}' terdaftar di Excel ({orig_target}).")
                                try:
                                    logger.remarks(f"{worker_tag}Menambahkan remarks '#0' pada rincian NIK ART '{art_title}'...")
                                    add_remarks_to_element(page, nik_box, note_text="#0", event_bus=self.event_bus, worker_prefix=worker_tag)
                                    matched_niks[web_nik_clean] = art_title
                                    logger.success(f"{worker_tag}Berhasil memberikan remarks '#0' pada NIK {orig_target} (ART: {art_title}).")
                                except Exception as e:
                                    err_msg = f"Gagal menambahkan catatan #0 pada NIK {orig_target} (ART: {art_title}): {e}"
                                    logger.error(f"{worker_tag}{err_msg}")
                                    has_error = True
                                    error_detail = err_msg
                                    break

                                # Optimasi Early Break: Jika semua target NIK sudah ketemu, hentikan iterasi sisa ART
                                if len(matched_niks) >= len(clean_targets) and len(matched_niks) >= total_nik:
                                    logger.info(f"{worker_tag}🚀 Seluruh target NIK ({len(matched_niks)} NIK) sudah berhasil ditemukan! Menghentikan pengecekan sisa anggota keluarga.")
                                    break
                            else:
                                logger.bot(f"{worker_tag}NIK {web_nik_clean} (ART: {art_title}) bukan target anomali R27. Lanjut.")

                        if has_error:
                            err_msg = f"GAGAL: {error_detail}"
                            self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                            continue

                        # 7. Evaluasi Hasil Pencocokan NIK
                        missing_niks = [orig for c_nik, orig in clean_targets.items() if c_nik not in matched_niks]

                        if missing_niks:
                            # Gagal: Tidak semua target NIK ditemukan di web penugasan
                            matched_summary = [f"{cn} ({name})" for cn, name in matched_niks.items()]
                            matched_text = ", ".join(matched_summary) if matched_summary else "Tidak ada"
                            missing_text = ", ".join(missing_niks)

                            err_msg = (
                                f"GAGAL: Hanya {len(matched_niks)} dari {len(clean_targets)} NIK sasaran yang ditemukan di web. "
                                f"NIK Belum Ditemukan: [{missing_text}]. "
                                f"NIK Berhasil Cocok: [{matched_text}]. "
                                f"Semua ART di Web: [{'; '.join(inspected_arts)}]."
                            )
                            logger.warning(f"⚠️ {worker_tag}{err_msg}")
                            self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                            continue

                        # 8. Semua Target NIK Berhasil Diremark -> Submit Formulir
                        logger.success(f"{worker_tag}Semua target NIK ({len(matched_niks)} NIK) berhasil cocok dan diremark '#0'!")
                        logger.bot(f"{worker_tag}Melanjutkan ke proses kirim formulir penugasan...")

                        submit_ok, submit_status, submit_msg = _submit_assignment_form(
                            page=page,
                            event_bus=self.event_bus,
                            row_idx=row_idx,
                            debug_review=self.debug_review_submit,
                            auto_minimize=self.auto_minimize,
                            worker_prefix=worker_tag
                        )

                        if not submit_ok:
                            err_msg = f"GAGAL: {submit_msg}. Catatan: {len(matched_niks)} NIK sudah diremark #0, namun submit gagal."
                            self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                            continue

                        # Sukses Penuh!
                        matched_summary = [f"{cn} ({name})" for cn, name in matched_niks.items()]
                        succ_ket = f"SUKSES: {len(matched_niks)} NIK [{', '.join(matched_summary)}] berhasil diremark #0 dan formulir penugasan berhasil disubmit."
                        logger.success(f"🎉 {worker_tag}Baris #{row_idx} SELESAI: {succ_ket}")

                        audit_data["status"] = "SUKSES"
                        audit_data["keterangan"] = succ_ket
                        audit_data["timestamp_end"] = datetime.now().isoformat()
                        audit_logger.record_row(audit_data)

                        with self.excel_lock:
                            try:
                                ExcelNIKR27Validator.update_row_status(self.excel_path, row_idx, "SUKSES", succ_ket)
                            except Exception as ex:
                                logger.error(f"{worker_tag}Gagal memperbarui status Excel: {ex}")

                        with self.stats_lock:
                            self.done_session += 1
                            self.processed_count += 1

                        self.event_bus.emit("row_completed", {
                            "row_idx": row_idx,
                            "status": "✅ SUKSES",
                            "keterangan": succ_ket,
                            "worker_id": worker_id
                        })

                        random_sleep(1.0, 1.8, event_bus=self.event_bus)

                    except Exception as e_row:
                        err_msg = f"GAGAL: Terjadi error tidak terduga pada baris #{row_idx}: {e_row}"
                        logger.error(f"❌ {worker_tag}{err_msg}")
                        self._record_row_failure(row_idx, err_msg, audit_data, worker_id)
                    finally:
                        try:
                            task_queue.task_done()
                        except ValueError:
                            pass

                # Tutup tab worker saat selesai
                if page:
                    try:
                        page.close()
                    except Exception:
                        pass
        except Exception as e_w:
            logger.error(f"❌ {worker_tag}Terjadi kesalahan fatal pada worker thread: {e_w}")

        logger.info(f"{worker_tag}Worker selesai bertugas.")

    def _record_row_failure(self, row_idx, err_msg, audit_data, worker_id):
        """Mencatat kegagalan baris secara thread-safe dan informatif."""
        audit_data["status"] = "GAGAL"
        audit_data["keterangan"] = err_msg
        audit_data["timestamp_end"] = datetime.now().isoformat()
        audit_logger.record_row(audit_data)

        with self.excel_lock:
            try:
                ExcelNIKR27Validator.update_row_status(self.excel_path, row_idx, "GAGAL", err_msg)
            except Exception as ex:
                logger.error(f"[W-{worker_id}] Gagal memperbarui status Excel: {ex}")

        with self.stats_lock:
            self.error_count += 1
            self.processed_count += 1

        self.event_bus.emit("row_completed", {
            "row_idx": row_idx,
            "status": "❌ GAGAL",
            "keterangan": err_msg,
            "worker_id": worker_id
        })

    def run(self):
        """Memulai proses otomasi Data Cleaning NIK R27 multi-worker."""
        self.event_bus.set_state(EngineState.RUNNING)
        logger.info(f"🚀 Memulai Otomasi Data Cleaning NIK R27 (Multi-Worker: {self.num_workers} Worker)...")

        # 1. Validasi awal berkas Excel
        val_res = ExcelNIKR27Validator.validate_excel_file(self.excel_path)
        if not val_res["valid"]:
            logger.error(f"Berkas Excel tidak valid: {val_res['error']}")
            self.event_bus.emit("engine_finished", {
                "status": "error",
                "message": val_res["error"],
                "total": 0, "done": 0, "error": 0, "skipped": 0
            })
            self.event_bus.set_state(EngineState.STOPPED)
            return

        rows = val_res["rows_data"]
        # Filter rentang baris
        target_rows = []
        for r in rows:
            rn = r["_row_num"]
            if rn < self.row_start:
                continue
            if self.row_end and rn > self.row_end:
                continue
            if r["_status_clean"] == "SUKSES":
                self.skipped_count += 1
                continue
            target_rows.append(r)

        if not target_rows:
            logger.info("ℹ️ Tidak ada baris yang perlu diproses (semua baris dalam rentang target sudah berstatus SUKSES).")
            self.event_bus.emit("engine_finished", {
                "status": "success",
                "message": "Semua baris target sudah selesai sebelumnya.",
                "total": 0, "done": 0, "error": 0, "skipped": self.skipped_count
            })
            self.event_bus.set_state(EngineState.STOPPED)
            return

        for r in target_rows:
            self.task_queue.put(r)

        total_targets = len(target_rows)
        logger.info(f"📋 Total {total_targets} baris antrean target akan diproses.")

        # 2. Hubungkan ke Chrome CDP
        # Pastikan browser Chrome sudah aktif di port debugging; jika belum, otomatis luncurkan
        cdp_active, _ = BrowserManager.is_cdp_running()
        if not cdp_active:
            logger.info("Browser Chrome belum aktif di port 9222. Meluncurkan Chrome otomatis...")
            launch_ok, launch_msg = BrowserManager.ensure_browser_ready()
            if not launch_ok:
                err_msg = (
                    "Gagal terhubung ke Chrome (Port 9222 belum aktif).\n"
                    "Penyebab: Chrome belum dijalankan dalam mode remote debugging port 9222.\n\n"
                    "Solusi Praktis:\n"
                    "1. Tutup seluruh jendela Google Chrome yang sedang terbuka.\n"
                    "2. Klik tombol '🚀 Luncurkan Chrome' di bagian atas aplikasi ini.\n"
                    "3. Pastikan indikator berubah menjadi '🟢 Terhubung (Chrome)'.\n"
                    "4. Klik '▶️ Mulai Otomasi' kembali."
                )
                logger.error(err_msg)
                self.event_bus.emit("engine_finished", {
                    "status": "error",
                    "message": err_msg,
                    "total": total_targets, "done": 0, "error": 0, "skipped": self.skipped_count
                })
                self.event_bus.set_state(EngineState.STOPPED)
                return
            time.sleep(1.5)

        # 3. Probe SSO Awal
        logger.info("Memeriksa status otentikasi SSO Fasih awal...")
        try:
            with sync_playwright() as p_probe:
                browser_probe = p_probe.chromium.connect_over_cdp(CDP_URL)
                context_probe = browser_probe.contexts[0] if browser_probe.contexts else browser_probe.new_context()
                page_probe = BrowserManager.find_authenticated_page(context_probe)
                if not page_probe:
                    page_probe = context_probe.pages[0] if context_probe.pages else context_probe.new_page()
                    if "fasih-sm.bps.go.id" not in page_probe.url:
                        try:
                            page_probe.goto("https://fasih-sm.bps.go.id/app", timeout=30000)
                        except Exception:
                            pass

                try:
                    page_probe.wait_for_load_state("domcontentloaded", timeout=4000)
                except Exception:
                    pass
                time.sleep(1.0)

                is_logged = BrowserManager.is_page_logged_in(page_probe)
                is_expired = BrowserManager.is_session_expired(page_probe)

                if not is_logged or is_expired:
                    logger.warning("⚠️ Terdeteksi sesi Fasih SSO belum login atau kedaluwarsa.")
                    page_probe = self._handle_relogin_needed(page_probe, context_probe, row_idx="Awal", is_midrun=False, worker_id=1)
                    if not page_probe or self.event_bus.is_stop_requested():
                        logger.warning("Otomasi dibatalkan sebelum login SSO selesai.")
                        self.event_bus.emit("all_completed", {
                            "done": 0, "error": 0, "skipped": self.skipped_count, "was_stopped": True
                        })
                        self.event_bus.set_state(EngineState.IDLE)
                        return
                else:
                    logger.success("✅ Sesi login Fasih SSO awal terverifikasi aktif.")
                    if self.auto_minimize:
                        WindowController.minimize_browser()
        except Exception as e_probe:
            logger.error(f"Gagal memeriksa status SSO Fasih: {e_probe}")
            self.event_bus.emit("all_completed", {
                "done": 0, "error": 0, "skipped": self.skipped_count, "was_stopped": False
            })
            self.event_bus.set_state(EngineState.IDLE)
            return

        # 4. Jalankan Worker Threads
        actual_workers = min(self.num_workers, total_targets)
        threads = []
        for w_id in range(1, actual_workers + 1):
            t = threading.Thread(
                target=self._worker_loop,
                args=(w_id, self.task_queue),
                daemon=True,
                name=f"CleaningNIKR27-Worker-{w_id}"
            )
            threads.append(t)
            t.start()
            time.sleep(0.5)

        # Tunggu semua worker selesai
        for t in threads:
            t.join()

        was_stopped = self.event_bus.is_stop_requested()
        self.event_bus.set_state(EngineState.IDLE)
        final_msg = f"Selesai! {self.done_session} baris berhasil disubmit, {self.error_count} baris gagal/perlu review."
        logger.info(f"🏁 {final_msg}")

        self.event_bus.emit("all_completed", {
            "done": self.done_session,
            "error": self.error_count,
            "skipped": self.skipped_count,
            "was_stopped": was_stopped
        })
