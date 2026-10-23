import os
import sys
import json
import time
import subprocess
import urllib.request
from urllib.parse import urlparse
from pathlib import Path
from config import CHROME_CANDIDATE_PATHS, CHROME_FLAGS, DEFAULT_CDP_PORT, CDP_URL
from core.logger import logger

class BrowserManager:
    @staticmethod
    def get_installed_browser_path():
        """Mencari path chrome.exe atau msedge.exe yang terpasang di sistem."""
        for candidate in CHROME_CANDIDATE_PATHS:
            if candidate.exists():
                return str(candidate)
        return None

    @staticmethod
    def is_cdp_running(port=DEFAULT_CDP_PORT, timeout=1.5):
        """Memeriksa apakah port debugging Chrome aktif."""
        try:
            url = f"http://127.0.0.1:{port}/json/version"
            req = urllib.request.Request(url, headers={"User-Agent": "Playwright"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                return True, data.get("Browser", "Chromium")
        except Exception:
            return False, None

    @classmethod
    def launch_browser(cls, target_url="https://fasih-sm.bps.go.id/app"):
        """Meluncurkan browser dengan port remote debugging dan membawanya ke jendela depan."""
        from core.window_controller import WindowController

        is_running, name = cls.is_cdp_running()
        if is_running:
            logger.info(f"Browser sudah aktif di port {DEFAULT_CDP_PORT} ({name}). Memfokuskan jendela...")
            WindowController.restore_and_focus_browser()
            return True, f"Browser sudah aktif ({name})"

        browser_exe = cls.get_installed_browser_path()
        if not browser_exe:
            logger.error("Tidak ditemukan instalasi Google Chrome atau Microsoft Edge di lokasi standar!")
            return False, "Google Chrome / Edge tidak ditemukan di laptop ini."

        logger.info(f"Meluncurkan browser: {Path(browser_exe).name}...")

        try:
            if sys.platform == "win32":
                # Gunakan perintah shell 'start' agar Chrome terbuka normal di jendela depan
                flags_str = " ".join(f'"{f}"' if " " in f else f for f in CHROME_FLAGS)
                cmd_line = f'start "" "{browser_exe}" {flags_str} "{target_url}"'
                subprocess.Popen(cmd_line, shell=True)
            else:
                subprocess.Popen([browser_exe] + CHROME_FLAGS + [target_url])

            # Tunggu port terbuka hingga 12 detik
            for _ in range(24):
                time.sleep(0.5)
                active, b_name = cls.is_cdp_running()
                if active:
                    logger.success(f"Browser berhasil diluncurkan & terhubung di port {DEFAULT_CDP_PORT} ({b_name}).")
                    time.sleep(0.5)
                    WindowController.restore_and_focus_browser()
                    return True, "Berhasil membuka browser"

            return False, "Browser diluncurkan tetapi port 9222 belum merespons."
        except Exception as e:
            logger.error(f"Gagal meluncurkan browser: {e}")
            return False, str(e)

    @classmethod
    def ensure_browser_ready(cls, target_url="https://fasih-sm.bps.go.id/app"):
        """Memastikan browser sudah aktif; jika belum, otomatis meluncurkannya."""
        is_running, name = cls.is_cdp_running()
        if is_running:
            from core.window_controller import WindowController
            WindowController.restore_and_focus_browser()
            return True, f"Browser sudah aktif ({name})"
        return cls.launch_browser(target_url)

    @staticmethod
    def is_session_expired(page):
        """
        Memeriksa apakah halaman saat ini menunjukkan sesi telah kedaluwarsa atau belum login.

        Karakteristik Sesi Kedaluwarsa / Belum Login di Fasih BPS:
        1. URL berada di domain SSO BPS: sso.bps.go.id
        2. URL berada di path auth login: /auth/login atau /login
        3. Elemen DOM login terlihat:
           - Teks / tombol: "Lanjutkan dengan SSO"
           - Teks: "Selamat Datang Kembali"
           - Subtitle: "Masuk ke akun Anda"
           - Form SSO Keycloak: #kc-form-login
        """
        try:
            if not page or page.is_closed():
                return False

            url = page.url.lower().strip()
            if not url or url == "about:blank":
                return True

            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            path = parsed.path.lower().rstrip("/")

            # 1. Cek jika berada di domain SSO BPS atau portal identitas
            if "sso.bps.go.id" in netloc or "sso" in netloc:
                return True

            # 2. Cek jika berada di path auth login atau root app (belum login)
            if "/auth/login" in path or path.endswith("/login") or path in ["/app", ""]:
                # Pada path /app atau root, cek apakah ada elemen login atau tidak ada elemen auth
                for sel in login_indicators:
                    try:
                        loc = page.locator(sel).first
                        if loc.count() > 0 and loc.is_visible():
                            return True
                    except Exception:
                        pass
                auth_selectors = [
                    "a[href*='logout']",
                    "button:has-text('Logout')",
                    "button:has-text('Keluar')",
                    ".fasih-form-sidebar",
                    "a:has-text('Survei')",
                    "a:has-text('Penugasan')"
                ]
                has_auth = False
                for sel in auth_selectors:
                    try:
                        loc = page.locator(sel).first
                        if loc.count() > 0 and loc.is_visible():
                            has_auth = True
                            break
                    except Exception:
                        pass
                if not has_auth:
                    return True

            # 3. Pengecekan elemen DOM spesifik halaman login Fasih
            login_indicators = [
                "a:has-text('Lanjutkan dengan SSO')",
                "button:has-text('Lanjutkan dengan SSO')",
                "span:has-text('Lanjutkan dengan SSO')",
                "text='Lanjutkan dengan SSO'",
                "h1:has-text('Selamat Datang Kembali')",
                "text='Selamat Datang Kembali'",
                "dd:has-text('Masuk ke akun Anda')",
                "a[href*='/auth/login']",
                "#kc-form-login",
                "#kc-login"
            ]
            for sel in login_indicators:
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        return True
                except Exception:
                    pass

            return False
        except Exception:
            return False

    @staticmethod
    def is_page_logged_in(page):
        """
        Memeriksa apakah halaman page sedang dalam sesi login Fasih yang sah (bukan SSO/login).

        Aturan Fasih BPS:
        1. Harus berada di domain fasih-sm.bps.go.id.
        2. TIDAK boleh berada di SSO BPS atau path /auth/login.
        3. TIDAK boleh ada elemen login ("Lanjutkan dengan SSO", "Selamat Datang Kembali", dsb).
        4. Pada path root (/app), harus terkonfirmasi memiliki indikator autentikasi (logout, menu survei, dsb).
        """
        try:
            if not page or page.is_closed():
                return False

            url = page.url.lower().strip()
            if not url or url == "about:blank":
                return False

            # Pastikan domain utama adalah Fasih
            if "fasih-sm.bps.go.id" not in url:
                return False

            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            path = parsed.path.lower().rstrip("/")

            # 1. Jika URL masih di domain SSO, Keycloak, OAuth, atau /login -> Belum login
            if any(k in url for k in ["sso.bps.go.id", "oauth2", "keycloak", "realms", "accounts.google"]):
                return False
            if "/auth/login" in path or path.endswith("/login"):
                return False

            # 2. Pengecekan selector login di DOM - jika ada yang terlihat, berarti belum login
            login_selectors = [
                "a:has-text('Lanjutkan dengan SSO')",
                "button:has-text('Lanjutkan dengan SSO')",
                "span:has-text('Lanjutkan dengan SSO')",
                "text='Lanjutkan dengan SSO'",
                "h1:has-text('Selamat Datang Kembali')",
                "text='Selamat Datang Kembali'",
                "dd:has-text('Masuk ke akun Anda')",
                "a[href*='/auth/login']",
                "#kc-form-login",
                "#kc-login"
            ]
            for sel in login_selectors:
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        return False
                except Exception:
                    pass

            # 3. Daftar indikator DOM autentikasi eksplisit
            auth_selectors = [
                "a[href*='logout']",
                "button:has-text('Logout')",
                "button:has-text('Keluar')",
                ".fasih-form-sidebar",
                "a:has-text('Survei')",
                "a:has-text('Penugasan')"
            ]

            # 4. Jika path adalah root /app atau root kosong
            if path in ["/app", ""]:
                for sel in auth_selectors:
                    try:
                        loc = page.locator(sel).first
                        if loc.count() > 0 and loc.is_visible():
                            return True
                    except Exception:
                        pass
                return False

            # 5. Indikator internal Fasih (survei, penugasan, monitoring, dashboard, dll)
            auth_subpaths = [
                "/surveys",
                "/survey",
                "/assignment",
                "/monitoring",
                "/dashboard",
                "/entri",
                "/pemeriksaan",
                "/alokasi",
                "/profile",
                "/wilayah"
            ]
            if any(p in path for p in auth_subpaths):
                # Pastikan tidak ada form login yang menutupi
                for sel in login_selectors:
                    try:
                        loc = page.locator(sel).first
                        if loc.count() > 0 and loc.is_visible():
                            return False
                    except Exception:
                        pass
                return True

            # 6. Fallback DOM di path lain
            for sel in auth_selectors:
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        return True
                except Exception:
                    pass

            return False
        except Exception:
            return False

    @classmethod
    def find_authenticated_page(cls, context):
        """
        Memindai seluruh tab terbuka di browser untuk menemukan tab yang sudah dalam sesi login Fasih.
        Mengembalikan page object jika ditemukan, atau None jika belum ada yang login.
        """
        if not context or not context.pages:
            return None

        for p in context.pages:
            try:
                if cls.is_page_logged_in(p):
                    return p
            except Exception:
                continue

        return None

    @classmethod
    def check_login_status_quick(cls, playwright_instance, cdp_url=CDP_URL):
        """
        Pemeriksaan cepat sesi login Fasih menggunakan instance Playwright.
        Mengembalikan tuple: (status_code, detail_pesan)
        status_code: 'LOGGED_IN', 'NOT_LOGGED_IN', 'SSO_WAITING', 'NO_PAGE', 'ERROR'
        """
        try:
            browser = playwright_instance.chromium.connect_over_cdp(cdp_url)
            if not browser.contexts or not browser.contexts[0].pages:
                browser.close()
                return "NO_PAGE", "Tidak ada halaman browser terbuka"

            context = browser.contexts[0]
            auth_page = cls.find_authenticated_page(context)
            if auth_page:
                browser.close()
                return "LOGGED_IN", "Sesi login Fasih aktif"

            # Periksa apakah ada halaman fasih atau sso yang terbuka
            has_fasih = any("fasih-sm.bps.go.id" in p.url for p in context.pages)
            has_sso = any("sso.bps.go.id" in p.url for p in context.pages)
            browser.close()

            if has_sso:
                return "SSO_WAITING", "Sedang di halaman login SSO BPS"
            elif has_fasih:
                return "NOT_LOGGED_IN", "Halaman Fasih terbuka namun belum login"
            else:
                return "NOT_FASIH", "Halaman fasih-sm.bps.go.id belum dibuka"
        except Exception as e:
            return "ERROR", str(e)

    @classmethod
    def perform_auto_login(cls, page, username, password, timeout=30000):
        """
        Melakukan proses login otomatis SSO BPS (khusus akun non-OTP), diadaptasi dari approve_tf.py:
        1. Memeriksa apakah halaman saat ini sudah berada di SSO Keycloak atau masih di Fasih.
        2. Jika di Fasih, mengeklik tombol 'Lanjutkan dengan SSO' atau login Fasih.
        3. Menunggu form login SSO (#username & #password).
        4. Mengisi username dan password, lalu menekan Enter atau submit form.
        5. Menunggu redirect kembali ke domain Fasih dan memvalidasi sesi aktif.
        Return: (success: bool, error_msg: str or None)
        """
        if not username or not password:
            return False, "Username atau Password SSO kosong"

        try:
            if not page or page.is_closed():
                return False, "Page browser tidak valid atau telah ditutup"

            logger.info("Memulai proses Auto-Login SSO BPS...")

            # 1. Cek apakah sudah di halaman SSO
            curr_url = page.url.lower()
            is_on_sso = "sso.bps.go.id" in curr_url or page.locator("#kc-form-login, #username").count() > 0

            if not is_on_sso:
                # Cari tombol login di Fasih
                login_btn_selectors = [
                    "a:has-text('Lanjutkan dengan SSO')",
                    "button:has-text('Lanjutkan dengan SSO')",
                    "span:has-text('Lanjutkan dengan SSO')",
                    "a.login-button[href*='oauth2']",
                    "a[href*='/auth/login']",
                    "button:has-text('Masuk')"
                ]

                clicked = False
                for btn_sel in login_btn_selectors:
                    try:
                        loc = page.locator(btn_sel).first
                        if loc.count() > 0 and loc.is_visible():
                            logger.info(f"Mengeklik tombol login Fasih ('{btn_sel}')...")
                            loc.click(timeout=8000)
                            clicked = True
                            break
                    except Exception:
                        pass

                if not clicked:
                    # Coba navigasi langsung ke landing page Fasih
                    try:
                        logger.info("Membuka https://fasih-sm.bps.go.id...")
                        page.goto("https://fasih-sm.bps.go.id", timeout=20000, wait_until="domcontentloaded")
                        time.sleep(1.5)
                        for btn_sel in login_btn_selectors:
                            try:
                                loc = page.locator(btn_sel).first
                                if loc.count() > 0 and loc.is_visible():
                                    loc.click(timeout=8000)
                                    break
                            except Exception:
                                pass
                    except Exception:
                        pass

            # 2. Tunggu form input SSO (#username)
            logger.info("Menunggu form login SSO BPS (#username)...")
            try:
                user_input = page.locator("#username, input[name='username']").first
                user_input.wait_for(state="visible", timeout=20000)
            except Exception:
                return False, "Form input SSO (#username) tidak muncul dalam batas waktu"

            time.sleep(0.4)
            # 3. Isi Username dan Password
            logger.info(f"Mengisikan kredensial SSO untuk user '{username}'...")
            user_input.fill(str(username).strip())
            time.sleep(0.3)

            pass_input = page.locator("#password, input[name='password']").first
            pass_input.wait_for(state="visible", timeout=10000)
            pass_input.fill(str(password).strip())
            time.sleep(0.3)

            # 4. Kirim Form (tekan Enter pada field password atau klik #kc-login)
            logger.info("Mengirim formulir login SSO...")
            submit_btn = page.locator("#kc-login, button[type='submit'], input[type='submit']").first
            if submit_btn.count() > 0 and submit_btn.is_visible():
                submit_btn.click(timeout=8000)
            else:
                pass_input.press("Enter")

            # 5. Tunggu respon autentikasi
            time.sleep(2.0)

            # Cek jika muncul pesan error kredensial salah
            error_elem = page.locator(".alert-error, #input-error, .kc-feedback-text, span.kc-feedback-text").first
            if error_elem.count() > 0 and error_elem.is_visible():
                err_text = error_elem.inner_text().strip()
                return False, f"Login ditolak oleh SSO BPS: '{err_text}'"

            # Cek jika muncul form OTP
            otp_elem = page.locator("#otp, input[name='otp']").first
            if otp_elem.count() > 0 and otp_elem.is_visible():
                return False, "Akun memerlukan kode OTP. Fitur Auto-Login khusus akun non-OTP, silakan gunakan mode Login Manual."

            # 6. Tunggu redirect kembali ke domain Fasih (maksimal 25 detik)
            start_wait = time.time()
            while time.time() - start_wait < 25:
                if cls.is_page_logged_in(page):
                    logger.success("Auto-Login SSO BPS berhasil diselesaikan!")
                    time.sleep(1.0)
                    return True, None
                time.sleep(1.0)

            # Cek terakhir
            if cls.is_page_logged_in(page):
                return True, None

            return False, "Timeout menunggu redirect ke aplikasi Fasih setelah submit SSO"

        except Exception as e:
            logger.error(f"Terjadi kesalahan saat Auto-Login: {e}")
            return False, str(e)

