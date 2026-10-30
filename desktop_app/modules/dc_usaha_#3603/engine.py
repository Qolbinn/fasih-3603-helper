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
from .selectors import (
    TOTAL_PENGELUARAN_SELECTOR,
    TOTAL_PENGELUARAN_BLN_SELECTOR,
    TOTAL_PENDAPATAN_SELECTOR,
    TOTAL_PENDAPATAN_BLN_SELECTOR,
    BLOK_II_XPATH,
    BLOK_CATATAN_XPATH,
    KIRIM_BUTTON_XPATH,
    CONFIRM_BUTTON_XPATH,
    RINGKASAN_KIRIM_SELECTOR,
    KONFIRMASI_KIRIM_BUTTON_SELECTOR,
    SUCCESS_SUBMIT_DIALOG_SELECTOR
)
from .validator import ExcelValidator

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
    try:
        loc.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    human_jitter(0.1, 0.2, event_bus=event_bus)
    loc.click(timeout=timeout, force=force)
    human_jitter(0.15, 0.3, event_bus=event_bus)

def find_total_container(page, field_type="pengeluaran", event_bus=None, worker_prefix=""):
    """
    Mencari container elemen total pengeluaran / pendapatan.
    Jika selector id standar tahunan tidak terdeteksi, memeriksa selector _bln (usaha baru buka 2026).
    Mengembalikan (locator, mode: 'TAHUNAN'|'BULANAN_2026', selector_used).
    """
    if field_type == "pengeluaran":
        thn_sel = TOTAL_PENGELUARAN_SELECTOR
        bln_sel = TOTAL_PENGELUARAN_BLN_SELECTOR
        label = "Total Pengeluaran"
    else:
        thn_sel = TOTAL_PENDAPATAN_SELECTOR
        bln_sel = TOTAL_PENDAPATAN_BLN_SELECTOR
        label = "Total Pendapatan"

    # 1. Coba deteksi selector tahunan
    thn_loc = page.locator(thn_sel)
    try:
        if thn_loc.count() > 0:
            for i in range(thn_loc.count()):
                el = thn_loc.nth(i)
                if el.is_visible():
                    return el, "TAHUNAN", thn_sel
            first_el = thn_loc.first
            if first_el.is_visible(timeout=3000):
                return first_el, "TAHUNAN", thn_sel
    except Exception:
        pass

    # 2. Jika tidak terdeteksi, alihkan ke selector _bln (bulanan / usaha baru buka 2026)
    bln_loc = page.locator(bln_sel)
    try:
        if bln_loc.count() > 0:
            for i in range(bln_loc.count()):
                el = bln_loc.nth(i)
                if el.is_visible():
                    logger.info(f"{worker_prefix}{label} tahunan tidak terdeteksi. Terdeteksi selector _bln (Usaha baru buka 2026): {bln_sel}")
                    return el, "BULANAN_2026", bln_sel
            first_el = bln_loc.first
            if first_el.is_visible(timeout=3000):
                logger.info(f"{worker_prefix}{label} tahunan tidak terdeteksi. Terdeteksi selector _bln (Usaha baru buka 2026): {bln_sel}")
                return first_el, "BULANAN_2026", bln_sel
    except Exception:
        pass

    return None, None, None

def check_has_existing_remark(page, container, field_name="elemen", event_bus=None, worker_prefix=""):
    """
    Membuka modal Catatan pada container dan memeriksa apakah sudah ada catatan sebelumnya (apapun isinya).
    Mengembalikan (has_existing: bool, existing_text: str).
    Modal selalu ditutup kembali.
    """
    try:
        container.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    random_sleep(0.3, 0.6, event_bus=event_bus)

    # Cari tombol Catatan yang visible
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
        raise Exception(f"Tombol Catatan visible tidak ditemukan pada {field_name}")

    safe_click(page, btn_catatan, timeout=20000, event_bus=event_bus)
    random_sleep(0.6, 1.0, event_bus=event_bus)

    dialog = page.locator("div[role='dialog']").first
    try:
        dialog.wait_for(state="visible", timeout=25000)
    except PlaywrightTimeoutError:
        raise Exception(f"Modal Catatan tidak muncul pada {field_name}")

    existing_notes = []
    try:
        bubbles = dialog.locator("div[class*='whitespace-pre-wrap'], div[class*='wrap-break-word'], div[class*='break-words']")
        for i in range(bubbles.count()):
            t = bubbles.nth(i).inner_text().strip()
            if t:
                existing_notes.append(t)
    except Exception:
        pass

    # Tutup dialog modal
    try:
        btn_close = dialog.locator("button[aria-label='Dismiss'], button[title='Tutup'], button:has-text('Tutup')").first
        if btn_close.is_visible(timeout=3000):
            safe_click(page, btn_close, timeout=8000, event_bus=event_bus)
        else:
            page.keyboard.press("Escape")
    except Exception:
        page.keyboard.press("Escape")

    try:
        dialog.wait_for(state="hidden", timeout=10000)
    except Exception:
        pass

    random_sleep(0.3, 0.5, event_bus=event_bus)

    if existing_notes:
        return True, " | ".join(existing_notes)
    return False, ""

def add_remarks_to_element(page, container_or_selector, note_text, event_bus=None, worker_prefix=""):
    """Membuka modal Catatan pada elemen container, mengetik catatan, klik simpan, lalu tutup modal."""
    if isinstance(container_or_selector, str):
        all_c = page.locator(container_or_selector)
        container = all_c.first
        if all_c.count() > 1:
            for i in range(all_c.count()):
                c = all_c.nth(i)
                if c.is_visible():
                    container = c
                    break
    else:
        container = container_or_selector

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
        raise Exception(f"Tombol Catatan visible tidak ditemukan pada container")

    safe_click(page, btn_catatan, timeout=20000, event_bus=event_bus)
    random_sleep(0.7, 1.1, event_bus=event_bus)

    dialog = page.locator("div[role='dialog']").first
    try:
        dialog.wait_for(state="visible", timeout=25000)
    except PlaywrightTimeoutError:
        raise Exception("Modal pop-up Catatan tidak muncul setelah tombol Catatan diklik")

    note_str = str(note_text).strip()

    # Cek apakah catatan sudah tercatat persis
    already_exists = False
    try:
        bubbles = dialog.locator("div[class*='whitespace-pre-wrap'], div[class*='wrap-break-word'], div[class*='break-words']")
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
        dialog.wait_for(state="hidden", timeout=12000)
    except Exception:
        pass

    random_sleep(0.4, 0.7, event_bus=event_bus)

def ensure_anomali_switch_active(page, event_bus=None, wait_timeout=35000, worker_prefix=""):
    """
    Pastikan switch 'Tampilkan Anomali Usaha dan Keluarga' (div#cek_anomali_button) AKTIF.
    - Sudah aktif (input aria-checked='true')  -> dibiarkan, tidak diklik.
    - Belum aktif (aria-checked='false')       -> klik kontrol switch, lalu verifikasi benar-benar aktif.
    Raise Exception jika elemen tidak muncul atau gagal diaktifkan.
    """
    box = page.locator("div#cek_anomali_button").first
    try:
        box.wait_for(state="visible", timeout=wait_timeout)
    except PlaywrightTimeoutError:
        try:
            box = page.locator("xpath=//div[@id='cek_anomali_button' or contains(@class, 'switch') or contains(., 'Tampilkan Anomali Usaha')]").first
            box.wait_for(state="visible", timeout=8000)
        except Exception:
            raise Exception("Switch 'Tampilkan Anomali Usaha dan Keluarga' tidak muncul di Blok Catatan.")

    try:
        box.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass

    sw_input = box.locator("input[role='switch']").first
    sw_control = box.locator("[id^='switch-'][id$='-control']").first
    if sw_control.count() == 0:
        sw_control = box.locator("span[class*='switch-thumb'], div[role='switch'], label").first

    target_click = sw_control if sw_control.count() > 0 else (sw_input if sw_input.count() > 0 else box)

    def _is_active():
        try:
            if sw_input.count() > 0:
                attr = sw_input.get_attribute("aria-checked")
                if attr == "true":
                    return True
                if sw_input.is_checked():
                    return True
        except Exception:
            pass
        try:
            attr_box = box.locator("[aria-checked='true']").first
            if attr_box.count() > 0:
                return True
            data_state = box.get_attribute("data-state")
            if data_state in ["checked", "active", "true"]:
                return True
        except Exception:
            pass
        return False

    if _is_active():
        logger.bot(f"{worker_prefix}Switch 'Tampilkan Anomali Usaha dan Keluarga' sudah aktif -> Dibiarkan.")
        return False

    logger.bot(f"{worker_prefix}Switch 'Tampilkan Anomali Usaha dan Keluarga' belum aktif -> Mengaktifkan...")
    for attempt in range(1, 4):
        target = target_click
        if attempt == 2 and sw_input.count() > 0:
            target = sw_input
        elif attempt == 3:
            target = box

        try:
            safe_click(page, target, timeout=5000, event_bus=event_bus, force=True)
        except Exception as click_err:
            logger.warning(f"{worker_prefix}Gagal klik switch kontrol (percobaan {attempt}/3): {click_err}")

        for _ in range(10):
            random_sleep(0.25, 0.35, event_bus=event_bus, allow_hesitation=False)
            if _is_active():
                logger.bot(f"{worker_prefix}Switch 'Tampilkan Anomali Usaha dan Keluarga' berhasil diaktifkan.")
                return True
        logger.warning(f"{worker_prefix}Switch anomali belum aktif setelah klik (percobaan {attempt}/3). Mengulang...")

    raise Exception("Gagal mengaktifkan toggle Tampilkan Anomali Usaha dan Keluarga.")

class SessionExpiredException(Exception):
    """Exception khusus saat sesi login Fasih terdeteksi expired di tengah proses."""
    pass

class DataCleaningEngine:
    def __init__(self, excel_path, event_bus, config_options=None):
        self.excel_path = excel_path
        self.event_bus = event_bus
        self.config_options = config_options or {}

        # Opsi baris target
        self.start_row_user = self.config_options.get("row_start") or self.config_options.get("start_row", 2)
        self.end_row_user = self.config_options.get("row_end") or self.config_options.get("end_row", None)

        # Multi-worker configuration
        raw_workers = self.config_options.get("num_workers", 1)
        try:
            self.num_workers = max(1, min(5, int(raw_workers)))
        except (ValueError, TypeError):
            self.num_workers = 1

        self.auto_minimize = self.config_options.get("auto_minimize", True)
        self.debug_review_submit = self.config_options.get("debug_review_submit", False)
        self.relogin_timeout_sec = int(self.config_options.get("relogin_timeout_sec", 180))

        # Auto Login SSO (Non-OTP)
        self.auth_mode = self.config_options.get("auth_mode", "manual")
        self.sso_username = self.config_options.get("sso_username", "").strip()
        self.sso_password = self.config_options.get("sso_password", "").strip()

        # Browser & CDP options
        self.browser_type = self.config_options.get("browser_type") or BrowserManager.get_active_browser()
        self.incognito = self.config_options.get("incognito") if self.config_options.get("incognito") is not None else BrowserManager.is_incognito_active()
        self.custom_cdp_url = self.config_options.get("cdp_url", "")
        self.task_queue = queue.Queue()

        # Statistics & Locks
        self.excel_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        self.reauth_lock = threading.Lock()
        self.processed_count = 0
        self.done_session = 0
        self.skipped_count = 0
        self.error_count = 0

    @property
    def success_count(self):
        return self.done_session

    @success_count.setter
    def success_count(self, val):
        self.done_session = val

    @property
    def cdp_url(self):
        if self.custom_cdp_url and self.custom_cdp_url.strip():
            return self.custom_cdp_url.strip()
        return BrowserManager.get_cdp_url(self.browser_type)

    def check_pause_and_stop(self, row_idx=None, audit_data=None, worker_id=1):
        if self.event_bus.is_stop_requested():
            logger.warning(f"[W-{worker_id}] Permintaan Berhenti (STOP) terdeteksi.")
            if audit_data:
                audit_data["status"] = "DIHENTIKAN"
                audit_data["keterangan"] = "Otomasi dihentikan pengguna"
                audit_logger.record_row(audit_data)
            return False

        if self.event_bus.is_paused():
            logger.info(f"[W-{worker_id}] Otomasi Dijeda (PAUSE). Menunggu pengguna melanjutkan...")
            self.event_bus.wait_if_paused()
            if self.event_bus.is_stop_requested():
                logger.warning(f"[W-{worker_id}] Permintaan Berhenti diterima saat dijeda.")
                return False
            logger.info(f"[W-{worker_id}] Otomasi Dilanjutkan (RESUME).")
        return True

    def _handle_relogin_needed(self, page, context, row_idx=None, nama_usaha=None, is_midrun=False, worker_id=1):
        """
        Menangani kondisi sesi Fasih SSO kedaluwarsa atau belum login.
        Dikoordinasikan secara thread-safe menggunakan reauth_lock.
        """
        worker_tag = f"[W-{worker_id}] " if worker_id else ""
        with self.reauth_lock:
            # Pengecekan cepat: apakah worker lain baru saja menyelesaikan re-login?
            if is_midrun:
                try:
                    if page and not page.is_closed() and BrowserManager.is_page_logged_in(page) and not BrowserManager.is_session_expired(page):
                        logger.info(f"{worker_tag}Sesi Fasih SSO telah dipulihkan oleh worker lain. Melanjutkan...")
                        return page
                except Exception:
                    pass

            b_label = "Microsoft Edge" if self.browser_type == "edge" else "Google Chrome"

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

            # Opsi 2 / Fallback: Mode Login Manual (meminta pengguna login di browser)
            if is_midrun and row_idx:
                prefix = f"Baris {row_idx} [{nama_usaha}]"
                msg = f"{worker_tag}Sesi Fasih kedaluwarsa di tengah jalan saat memproses {prefix}. Silakan login kembali di {b_label}, lalu klik '🟢 Saya Sudah Login'."
                logger.warning(f"⚠️ {worker_tag}{prefix}: Sesi Fasih SSO kedaluwarsa di tengah jalan! Menjeda seluruh worker & menampilkan {b_label}...")
            else:
                prefix = "Pemeriksaan Sesi Awal"
                msg = f"Sesi Fasih SSO belum terdeteksi. Silakan login SSO BPS di {b_label}, lalu klik '🟢 Saya Sudah Login'."
                logger.warning(f"⚠️ {prefix}: Sesi Fasih SSO belum aktif. Menampilkan jendela {b_label}...")

            WindowController.restore_and_focus_browser()

            # Reset flag konfirmasi manual sebelumnya
            self.event_bus.reset_auth_confirmation()

            self.event_bus.emit("auth_waiting", {
                "message": msg,
                "is_midrun": is_midrun,
                "row_idx": row_idx,
                "worker_id": worker_id
            })
            logger.info(f"{worker_tag}Menunggu Anda login SSO BPS di {b_label} ({'Mid-Run Baris ' + str(row_idx) if is_midrun else 'Awal'})...")

            active_page = page
            while True:
                # 1. Periksa jika ada permintaan stop dari user
                if self.event_bus.is_stop_requested():
                    logger.warning(f"{worker_tag}Otomasi dihentikan oleh pengguna saat menunggu login SSO.")
                    return None

                # 2. Periksa konfirmasi manual dari tombol UI '🟢 Saya Sudah Login'
                if self.event_bus.is_auth_confirmed():
                    logger.success(f"🟢 {worker_tag}Konfirmasi login diterima dari pengguna! Memeriksa tab browser...")
                    detected = BrowserManager.find_authenticated_page(context)
                    if detected:
                        active_page = detected
                    elif not active_page or active_page.is_closed():
                        active_page = context.pages[0] if context.pages else None
                    break

                # 3. Pindai secara dinamis tab aktif atau tab lain yang terbuka di context (Auto-detect)
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

            # Reset flag konfirmasi
            self.event_bus.reset_auth_confirmation()

            # Pastikan active_page masih valid
            if not active_page or active_page.is_closed():
                active_page = BrowserManager.find_authenticated_page(context)
                if not active_page and context.pages:
                    active_page = context.pages[0]

            # Tunggu load state pasca redirect login
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

    def _navigate_assignment_page(self, page, raw_url, row_idx=None, nama_usaha="", worker_prefix=""):
        logger.bot(f"{worker_prefix}Membuka tautan: {raw_url}")
        try:
            page.goto(raw_url, timeout=60000, wait_until="commit")
        except Exception as e_goto:
            logger.warning(f"{worker_prefix}Peringatan goto: {e_goto}. Mencoba menunggu networkidle...")
        random_sleep(1.5, 2.5, event_bus=self.event_bus)

        # Tunggu container formulir atau sidebar siap
        try:
            page.locator(".fasih-form-sidebar, div[class*='sidebar'], button#btn-kirim, button:has-text('Kirim')").first.wait_for(state="attached", timeout=45000)
        except Exception:
            pass

    def _process_single_assignment(self, worker_id, page, context, row_idx, wb, sheet, col_map, end_r, target_total):
        w_tag = f"[W-{worker_id}] "

        url_col = col_map.get("url")
        id_col = col_map.get("id")
        name_col = col_map.get("nama_usaha")
        status_col = col_map.get("status")
        ket_col = col_map.get("keterangan")

        with self.excel_lock:
            url_val = sheet.cell(row=row_idx, column=url_col).value if url_col else None
            assignment_id = str(sheet.cell(row=row_idx, column=id_col).value or "").strip() if id_col else ""
            nama_usaha = str(sheet.cell(row=row_idx, column=name_col).value or "").strip() if name_col else ""
            status_val = str(sheet.cell(row=row_idx, column=status_col).value or "").strip() if status_col else ""

        if not url_val or str(url_val).strip() == "":
            return

        with self.stats_lock:
            self.processed_count += 1
            curr_proc = self.processed_count

        self.event_bus.emit("progress_updated", {
            "current": curr_proc,
            "total": target_total,
            "row_idx": row_idx,
            "nama_usaha": nama_usaha,
            "assignment_id": assignment_id,
            "worker_id": worker_id
        })

        if status_val.upper() in ["SUKSES", "DONE", "SELESAI", "BERHASIL"]:
            with self.excel_lock:
                existing_ket = str(sheet.cell(row=row_idx, column=ket_col).value or "").strip() if ket_col else ""
            logger.info(f"{w_tag}Baris {row_idx} [{nama_usaha}] berstatus {status_val} -> Dilewati.")
            with self.stats_lock:
                self.skipped_count += 1
            self.event_bus.emit("row_completed", {
                "row_idx": row_idx,
                "status": f"{status_val} (LEWAT)",
                "keterangan": existing_ket,
                "worker_id": worker_id
            })
            return

        try:
            file_label = Path(self.excel_path).stem[:10] if self.excel_path else "Fasih"
            page.evaluate(f"() => {{ document.title = '[{file_label}|W-{worker_id}] {nama_usaha[:16]}'; }}")
        except Exception:
            pass

        self.event_bus.emit("worker_status_updated", {
            "worker_id": worker_id,
            "status": "BUSY",
            "row_idx": row_idx,
            "nama_usaha": nama_usaha
        })

        logger.bot(f"{w_tag}--- [Baris {row_idx}/{end_r}] Memproses: {nama_usaha or assignment_id or url_val} ---")
        self.event_bus.emit("row_started", {
            "row_idx": row_idx,
            "nama_usaha": nama_usaha,
            "id": assignment_id,
            "worker_id": worker_id
        })

        audit_data = {
            "row_index": row_idx,
            "assignment_id": assignment_id,
            "nama_usaha": nama_usaha,
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
                    # STEP 1: Buka URL Penugasan
                    self._navigate_assignment_page(page, raw_url, row_idx=row_idx, nama_usaha=nama_usaha, worker_prefix=w_tag)

                    if BrowserManager.is_session_expired(page) or not BrowserManager.is_page_logged_in(page):
                        raise SessionExpiredException("Sesi login Fasih tidak aktif atau kedaluwarsa saat membuka formulir.")

                    # STEP 2: Buka Sub Sidebar Blok II / Nama Usaha
                    if not self.check_pause_and_stop(row_idx, audit_data, worker_id):
                        return

                    try:
                        try:
                            page.locator(".fasih-form-sidebar, div[class*='sidebar']").first.wait_for(state="visible", timeout=35000)
                        except Exception:
                            pass

                        try:
                            page.locator(BLOK_II_XPATH).first.wait_for(state="visible", timeout=35000)
                            safe_click(page, BLOK_II_XPATH, timeout=25000, event_bus=self.event_bus)
                        except Exception:
                            safe_click(page, "div[title*='BLOK II'], *[title*='BLOK II']", timeout=20000, event_bus=self.event_bus)
                        random_sleep(0.8, 1.4, event_bus=self.event_bus)
                    except Exception as blok2_err:
                        if BrowserManager.is_session_expired(page) or not BrowserManager.is_page_logged_in(page):
                            raise SessionExpiredException(f"Sesi login Fasih kedaluwarsa saat membuka Blok II: {blok2_err}")
                        raise blok2_err

                    # Cari item nama usaha di sub-sidebar jika tersedia
                    usaha_item = None
                    if nama_usaha:
                        usaha_xpath = f"xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[contains(@class, 'cursor-pointer') and contains(., '{nama_usaha}')] | //div[contains(@class, 'cursor-pointer') and contains(., '{nama_usaha}')]"
                        if page.locator(usaha_xpath).first.count() > 0:
                            usaha_item = page.locator(usaha_xpath).first

                    if not usaha_item:
                        first_sub = page.locator("xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[contains(@class, 'cursor-pointer') and not(contains(., 'BLOK II')) and not(contains(., 'CATATAN'))] | //div[contains(@class, 'cursor-pointer') and not(contains(., 'BLOK II')) and not(contains(., 'CATATAN'))]").first
                        if first_sub.count() > 0:
                            usaha_item = first_sub

                    if usaha_item:
                        safe_click(page, usaha_item, timeout=25000, event_bus=self.event_bus)
                        random_sleep(1.5, 2.5, event_bus=self.event_bus)

                    # STEP 3: Deteksi Container Total Pengeluaran & Total Pendapatan
                    if not self.check_pause_and_stop(row_idx, audit_data, worker_id):
                        return

                    elem_pengeluaran, mode_p, sel_p = find_total_container(page, "pengeluaran", event_bus=self.event_bus, worker_prefix=w_tag)
                    if not elem_pengeluaran:
                        raise Exception("Elemen Total Pengeluaran (baik tahunan maupun bulanan) tidak ditemukan pada formulir.")

                    elem_pendapatan, mode_pend, sel_pend = find_total_container(page, "pendapatan", event_bus=self.event_bus, worker_prefix=w_tag)
                    if not elem_pendapatan:
                        raise Exception("Elemen Total Pendapatan (baik tahunan maupun bulanan) tidak ditemukan pada formulir.")

                    logger.bot(f"{w_tag}Rincian terdeteksi: Total Pengeluaran [{mode_p}], Total Pendapatan [{mode_pend}].")

                    # STEP 4: Pengecekan Catatan Sebelumnya (SKIP jika sudah ada remark)
                    logger.bot(f"{w_tag}Memeriksa riwayat catatan pada Total Pengeluaran...")
                    has_p, note_p = check_has_existing_remark(page, elem_pengeluaran, "Total Pengeluaran", event_bus=self.event_bus, worker_prefix=w_tag)
                    if has_p:
                        skip_msg = f"Sudah ada catatan pada Total Pengeluaran ('{note_p}'). Dilewati."
                        logger.success(f"{w_tag}Baris {row_idx} [{nama_usaha}]: {skip_msg} Status diset SUKSES.")
                        with self.stats_lock:
                            self.done_session += 1
                        with self.excel_lock:
                            if status_col: sheet.cell(row=row_idx, column=status_col, value="SUKSES")
                            if ket_col: sheet.cell(row=row_idx, column=ket_col, value=skip_msg)
                            try:
                                wb.save(self.excel_path)
                            except Exception:
                                pass
                        audit_data["status"] = "SUKSES"
                        audit_data["keterangan"] = skip_msg
                        audit_logger.record_row(audit_data)
                        self.event_bus.emit("row_completed", {
                            "row_idx": row_idx,
                            "status": "SUKSES",
                            "keterangan": skip_msg,
                            "worker_id": worker_id
                        })
                        return

                    logger.bot(f"{w_tag}Memeriksa riwayat catatan pada Total Pendapatan...")
                    has_pend, note_pend = check_has_existing_remark(page, elem_pendapatan, "Total Pendapatan", event_bus=self.event_bus, worker_prefix=w_tag)
                    if has_pend:
                        skip_msg = f"Sudah ada catatan pada Total Pendapatan ('{note_pend}'). Dilewati."
                        logger.success(f"{w_tag}Baris {row_idx} [{nama_usaha}]: {skip_msg} Status diset SUKSES.")
                        with self.stats_lock:
                            self.done_session += 1
                        with self.excel_lock:
                            if status_col: sheet.cell(row=row_idx, column=status_col, value="SUKSES")
                            if ket_col: sheet.cell(row=row_idx, column=ket_col, value=skip_msg)
                            try:
                                wb.save(self.excel_path)
                            except Exception:
                                pass
                        audit_data["status"] = "SUKSES"
                        audit_data["keterangan"] = skip_msg
                        audit_logger.record_row(audit_data)
                        self.event_bus.emit("row_completed", {
                            "row_idx": row_idx,
                            "status": "SUKSES",
                            "keterangan": skip_msg,
                            "worker_id": worker_id
                        })
                        return

                    # STEP 5: Memberikan Catatan Remark
                    # 1. Total Pengeluaran = #0
                    logger.remarks(f"{w_tag}Memberikan catatan '#0' pada Total Pengeluaran ({mode_p})...")
                    add_remarks_to_element(page, elem_pengeluaran, "#0", event_bus=self.event_bus, worker_prefix=w_tag)
                    audit_data["remarks_pengeluaran"] = f"#0 ({mode_p})"

                    # 2. Total Pendapatan = #3603
                    logger.remarks(f"{w_tag}Memberikan catatan '#3603' pada Total Pendapatan ({mode_pend})...")
                    add_remarks_to_element(page, elem_pendapatan, "#3603", event_bus=self.event_bus, worker_prefix=w_tag)
                    audit_data["remarks_pendapatan"] = f"#3603 ({mode_pend})"

                    # STEP 6: Menuju Blok Catatan di Sidebar
                    if not self.check_pause_and_stop(row_idx, audit_data, worker_id):
                        return

                    try:
                        page.locator(BLOK_CATATAN_XPATH).first.wait_for(state="visible", timeout=35000)
                        safe_click(page, BLOK_CATATAN_XPATH, timeout=25000, event_bus=self.event_bus)
                    except Exception:
                        safe_click(page, "div[title='CATATAN'], *[title='CATATAN']", timeout=25000, event_bus=self.event_bus)
                    random_sleep(1.2, 2.0, event_bus=self.event_bus)

                    # STEP 7: Switch Tampilkan Anomali Usaha dan Keluarga
                    if not self.check_pause_and_stop(row_idx, audit_data, worker_id):
                        return

                    ensure_anomali_switch_active(page, event_bus=self.event_bus, wait_timeout=35000, worker_prefix=w_tag)
                    random_sleep(1.8, 2.5, event_bus=self.event_bus, allow_hesitation=False)

                    # STEP 8: Submit Flow Berantai (4 Langkah)
                    if not self.check_pause_and_stop(row_idx, audit_data, worker_id):
                        return

                    logger.bot(f"{w_tag}[1/4] Mengklik tombol Kirim formulir Fasih...")
                    form_kirim_btn = page.locator("button#btn-kirim, button:has-text('Kirim')").first
                    if form_kirim_btn.count() == 0 or not form_kirim_btn.is_visible():
                        form_kirim_btn = page.locator(KIRIM_BUTTON_XPATH).first

                    if form_kirim_btn.count() == 0:
                        raise Exception("Tombol Kirim pada formulir Fasih tidak ditemukan.")

                    safe_click(page, form_kirim_btn, timeout=25000, event_bus=self.event_bus, force=True)
                    random_sleep(1.0, 1.8, event_bus=self.event_bus, allow_hesitation=False)

                    # Langkah 2: Pop-up validasi Galat
                    btn_konfirmasi = page.locator(KONFIRMASI_KIRIM_BUTTON_SELECTOR).last
                    if not btn_konfirmasi.is_visible(timeout=2500):
                        logger.bot(f"{w_tag}[2/4] Menunggu pop-up validasi Kirim...")
                        dialog = page.locator("div[role='dialog'], div[role='alertdialog'], div:has(button:has-text('Batal')):has(button:has-text('Kirim'))").last
                        dialog.wait_for(state="visible", timeout=25000)
                        random_sleep(0.5, 0.8, event_bus=self.event_bus, allow_hesitation=False)

                        galat_count = 0
                        try:
                            galat_card = dialog.locator("button:has-text('Galat')").first
                            if galat_card.count() > 0 and galat_card.is_visible():
                                card_text = galat_card.inner_text().strip()
                                lines = [l.strip() for l in card_text.split("\n") if l.strip()]
                                for line in lines:
                                    if line.isdigit():
                                        galat_count = int(line)
                                        break
                                else:
                                    nums = re.findall(r"\b\d+\b", card_text)
                                    if nums:
                                        galat_count = int(nums[0])
                        except Exception as e_card:
                            logger.bot(f"{w_tag}Catatan kartu galat: {e_card}")

                        audit_data["galat_count"] = galat_count

                        if galat_count > 0:
                            err_msg = f"Terdapat {galat_count} Galat yang perlu diperbaiki. Submit dibatalkan."
                            logger.warning(f"⚠️ {w_tag}Baris {row_idx} [{nama_usaha}]: {err_msg}")

                            try:
                                btn_batal = dialog.locator("button:has-text('Batal')").first
                                if btn_batal.is_visible(timeout=3000):
                                    safe_click(page, btn_batal, timeout=5000, event_bus=self.event_bus)
                                else:
                                    page.keyboard.press("Escape")
                            except Exception:
                                page.keyboard.press("Escape")

                            with self.excel_lock:
                                if status_col: sheet.cell(row=row_idx, column=status_col).value = f"GAGAL ({galat_count} Galat)"
                                if ket_col: sheet.cell(row=row_idx, column=ket_col).value = err_msg
                                try:
                                    wb.save(self.excel_path)
                                except Exception:
                                    pass

                            with self.stats_lock:
                                self.error_count += 1

                            audit_data["status"] = "GAGAL"
                            audit_data["keterangan"] = err_msg
                            audit_logger.record_row(audit_data)

                            self.event_bus.emit("row_completed", {
                                "row_idx": row_idx,
                                "status": f"GAGAL ({galat_count} Galat)",
                                "keterangan": err_msg,
                                "worker_id": worker_id
                            })
                            return

                        logger.bot(f"{w_tag}[2/4] Galat = 0. Mengklik tombol Kirim pada pop-up validasi...")
                        btn_kirim_dialog = dialog.locator("button:has-text('Kirim')").last
                        safe_click(page, btn_kirim_dialog, timeout=20000, event_bus=self.event_bus)
                        random_sleep(1.5, 2.2, event_bus=self.event_bus, allow_hesitation=False)

                    # Langkah 3: Konfirmasi Kirim
                    logger.bot(f"{w_tag}[3/4] Menunggu pop-up Konfirmasi Kirim...")
                    btn_konfirmasi = page.locator(KONFIRMASI_KIRIM_BUTTON_SELECTOR).last
                    btn_konfirmasi.wait_for(state="visible", timeout=30000)
                    random_sleep(0.5, 1.0, event_bus=self.event_bus, allow_hesitation=False)

                    if self.debug_review_submit:
                        logger.warning(f"🔍 [MODE REVIEW DEBUGGING] {w_tag}Baris {row_idx} [{nama_usaha}]: Modal Konfirmasi Kirim terbuka.")
                        WindowController.restore_and_focus_browser()
                        self.event_bus.emit("waiting_confirm_submit", {
                            "row_idx": row_idx,
                            "nama_usaha": nama_usaha,
                            "worker_id": worker_id
                        })
                        self.event_bus.wait_for_submit_confirmation()

                        if self.event_bus.is_stop_requested():
                            logger.warning(f"{w_tag}Proses dihentikan sebelum konfirmasi submit.")
                            return

                        logger.bot(f"{w_tag}Konfirmasi diterima dari pengguna. Mengklik tombol Konfirmasi...")
                        safe_click(page, btn_konfirmasi, timeout=20000, event_bus=self.event_bus, force=True)
                        if self.auto_minimize:
                            WindowController.minimize_browser()
                    else:
                        logger.bot(f"{w_tag}[3/4] Dialog Konfirmasi Kirim aktif. Mengklik tombol Konfirmasi...")
                        safe_click(page, btn_konfirmasi, timeout=20000, event_bus=self.event_bus, force=True)

                    # Langkah 4: Menunggu Dialog Sukses
                    logger.bot(f"{w_tag}[4/4] Menunggu server memproses submit...")
                    success_dialog = page.locator(SUCCESS_SUBMIT_DIALOG_SELECTOR).first

                    try:
                        success_dialog.wait_for(state="visible", timeout=50000)
                        logger.success(f"🎉 {w_tag}Baris {row_idx} [{nama_usaha}]: Berhasil disubmit!")

                        try:
                            btn_tetap = page.locator("button:has-text('Tetap di Halaman')").first
                            if btn_tetap.is_visible(timeout=2000):
                                safe_click(page, btn_tetap, timeout=5000, event_bus=self.event_bus)
                        except Exception:
                            pass

                        succ_ket = f"Sukses (Pengeluaran: #0 [{mode_p}], Pendapatan: #3603 [{mode_pend}])"
                        with self.excel_lock:
                            if status_col: sheet.cell(row=row_idx, column=status_col).value = "SUKSES"
                            if ket_col: sheet.cell(row=row_idx, column=ket_col).value = succ_ket
                            try:
                                wb.save(self.excel_path)
                            except Exception:
                                pass

                        with self.stats_lock:
                            self.done_session += 1

                        audit_data["status"] = "SUKSES"
                        audit_data["keterangan"] = succ_ket
                        audit_logger.record_row(audit_data)

                        self.event_bus.emit("row_completed", {
                            "row_idx": row_idx,
                            "status": "✅ SUKSES",
                            "keterangan": succ_ket,
                            "worker_id": worker_id
                        })
                        return

                    except PlaywrightTimeoutError:
                        logger.warning(f"⚠️ {w_tag}Timeout menunggu dialog sukses submit.")
                        with self.excel_lock:
                            if status_col: sheet.cell(row=row_idx, column=status_col).value = "PERIKSA MANUAL"
                            if ket_col: sheet.cell(row=row_idx, column=ket_col).value = "Submit diklik, namun konfirmasi akhir timeout"
                            try:
                                wb.save(self.excel_path)
                            except Exception:
                                pass

                        with self.stats_lock:
                            self.error_count += 1

                        self.event_bus.emit("row_completed", {
                            "row_idx": row_idx,
                            "status": "⚠️ PERIKSA MANUAL",
                            "keterangan": "Timeout dialog konfirmasi submit",
                            "worker_id": worker_id
                        })
                        return

                except SessionExpiredException as e_reauth:
                    reauth_count += 1
                    if reauth_count > max_reauth_attempts:
                        raise e_reauth
                    logger.warning(f"{w_tag}Sesi Fasih kedaluwarsa (Percobaan {reauth_count}/{max_reauth_attempts}).")
                    reauth_ok = self._handle_relogin_needed(page, context, row_idx=row_idx, nama_usaha=nama_usaha, is_midrun=True, worker_id=worker_id)
                    if not reauth_ok:
                        raise Exception("Sesi Fasih kedaluwarsa dan tidak berhasil diautentikasi ulang.")
                    page = reauth_ok

        except Exception as e_row:
            err_str = str(e_row)
            logger.error(f"❌ {w_tag}Baris {row_idx} [{nama_usaha}] GAGAL: {err_str}")
            with self.excel_lock:
                if status_col: sheet.cell(row=row_idx, column=status_col).value = "GAGAL"
                if ket_col: sheet.cell(row=row_idx, column=ket_col).value = err_str
                try:
                    wb.save(self.excel_path)
                except Exception:
                    pass

            with self.stats_lock:
                self.error_count += 1

            audit_data["status"] = "GAGAL"
            audit_data["keterangan"] = err_str
            audit_logger.record_row(audit_data)

            self.event_bus.emit("row_completed", {
                "row_idx": row_idx,
                "status": "❌ GAGAL",
                "keterangan": err_str,
                "worker_id": worker_id
            })

    def run(self):
        """Metode utama eksekusi worker otomasi multi-threading."""
        self.event_bus.set_state(EngineState.RUNNING)
        logger.bot("========================================================")
        logger.bot(f"  Memulai Otomasi: DC Usaha #3603 ({self.num_workers} Worker)")
        logger.bot(f"  Target File: {self.excel_path}")
        logger.bot("========================================================")

        try:
            wb = openpyxl.load_workbook(self.excel_path)
            sheet = wb.active
        except Exception as e_load:
            logger.error(f"Gagal memuat berkas Excel: {e_load}")
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

        # 3. Pemeriksaan Otentikasi Awal SSO Fasih menggunakan probe ringan
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
                    relogin_ok = self._handle_relogin_needed(page_probe, context_probe, is_midrun=False, worker_id=1)
                    if not relogin_ok or self.event_bus.is_stop_requested():
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

        # 4. Kolom mapping index & persiapan baris
        header_map = {}
        for c in range(1, sheet.max_column + 1):
            val = sheet.cell(row=1, column=c).value
            if val is not None:
                header_map[str(val).strip().lower()] = c

        from .selectors import EXCEL_COLUMNS_CONFIG
        col_map = {}
        for key, aliases in EXCEL_COLUMNS_CONFIG.items():
            for alias in aliases:
                if alias.lower() in header_map:
                    col_map[key] = header_map[alias.lower()]
                    break

        # Pastikan kolom status & keterangan ada
        with self.excel_lock:
            if "status" not in col_map:
                new_col = sheet.max_column + 1
                sheet.cell(row=1, column=new_col, value="Status")
                col_map["status"] = new_col
            if "keterangan" not in col_map:
                new_col = sheet.max_column + 1
                sheet.cell(row=1, column=new_col, value="Keterangan")
                col_map["keterangan"] = new_col
            wb.save(self.excel_path)

        start_r = max(2, self.start_row_user)
        end_r = self.end_row_user if (self.end_row_user and self.end_row_user <= sheet.max_row) else sheet.max_row

        url_c = col_map.get("url")
        target_rows = [
            r for r in range(start_r, end_r + 1)
            if url_c and sheet.cell(row=r, column=url_c).value and str(sheet.cell(row=r, column=url_c).value).strip() != ""
        ]
        target_total = len(target_rows)

        if target_total == 0:
            logger.warning("Tidak ditemukan baris URL penugasan valid untuk diproses.")
            wb.close()
            self.event_bus.set_state(EngineState.IDLE)
            self.event_bus.emit("all_completed", {
                "done": 0, "error": 0, "skipped": 0, "was_stopped": False
            })
            return

        actual_workers = min(self.num_workers, target_total)
        logger.info(f"Total baris yang akan diproses: {target_total} (Baris {start_r} s.d. {end_r}). Mengaktifkan {actual_workers} Worker.")

        for r in target_rows:
            self.task_queue.put(r)

        def worker_runner(w_id):
            w_tag = f"[W-{w_id}] "
            try:
                with sync_playwright() as p_worker:
                    browser = p_worker.chromium.connect_over_cdp(self.cdp_url)
                    context = browser.contexts[0]

                    file_label = Path(self.excel_path).stem[:10] if self.excel_path else "Fasih"
                    page = context.new_page()

                    try:
                        page.evaluate(f"() => {{ document.title = '[{file_label}|W-{w_id}] Fasih 3603 Helper'; }}")
                    except Exception:
                        pass

                    self.event_bus.emit("worker_status_updated", {
                        "worker_id": w_id, "status": "IDLE", "row_idx": None, "nama_usaha": ""
                    })
                    logger.info(f"{w_tag}Tab worker siap beroperasi.")

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
                                    page.evaluate(f"() => {{ document.title = '[{file_label}|W-{w_id}] Fasih 3603 Helper'; }}")
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
                            random_sleep(1.0, 2.0, event_bus=self.event_bus)

                    # Bersihkan tab khusus saat worker selesai
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
                t = threading.Thread(target=worker_runner, args=(w_id,), name=f"DCUsahaWorker-{w_id}")
                t.start()
                threads.append(t)
                time.sleep(0.4)

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
            logger.warning(f"⏹️ Otomasi Dihentikan oleh Pengguna! (Sukses: {self.done_session}, Gagal: {self.error_count}, Dilewati: {self.skipped_count})")
        else:
            logger.success(f"🏁 Eksekusi DC Usaha #3603 Selesai! (Sukses: {self.done_session}, Gagal: {self.error_count}, Dilewati: {self.skipped_count})")

        self.event_bus.emit("all_completed", {
            "done": self.done_session,
            "error": self.error_count,
            "skipped": self.skipped_count,
            "was_stopped": was_stopped
        })

CleaningUsahaEngine = DataCleaningEngine
DCUsaha3603Engine = DataCleaningEngine
