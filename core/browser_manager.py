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
        1. URL diarahkan ke halaman login root:
           https://fasih-sm.bps.go.id/app atau https://fasih-sm.bps.go.id/app/
        2. URL berada di subdomain SSO atau halaman login auth:
           sso.bps.go.id, /auth/login, /login, keycloak, dsb.
        3. DOM mengandung tombol / teks login:
           - "Lanjutkan dengan SSO"
           - "Selamat Datang Kembali"
           - "Masuk ke akun Anda"
           - Form login SSO / Keycloak
        """
        try:
            url = page.url.lower().strip()
            if not url or url == "about:blank":
                return False

            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            path = parsed.path.lower().rstrip("/")

            # 1. Cek jika berada di domain SSO BPS atau portal identitas
            if "sso.bps.go.id" in netloc or "sso" in netloc:
                return True

            # 2. Cek jika di domain fasih-sm.bps.go.id tapi berada di path login/auth
            if "fasih-sm.bps.go.id" in netloc:
                # Path login root Fasih: /app, /app/auth/login, atau root /
                if path in ["/app", ""]:
                    return True
                if "/auth/login" in path or path.endswith("/login"):
                    return True

            # 3. Pengecekan elemen DOM spesifik halaman login Fasih
            login_indicators = [
                "text='Lanjutkan dengan SSO'",
                "text='Selamat Datang Kembali'",
                "a[href*='/auth/login']",
                "#kc-form-login",
                "#kc-login"
            ]
            for sel in login_indicators:
                try:
                    if page.locator(sel).first.count() > 0:
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
        1. URL Login: https://fasih-sm.bps.go.id/app (atau halaman SSO sso.bps.go.id).
        2. URL Setelah Login: Fasih otomatis me-redirect ke:
           https://fasih-sm.bps.go.id/app/surveys... atau /app/assignment/..., /monitoring, dll.
        """
        try:
            url = page.url.lower().strip()
            if not url or url == "about:blank":
                return False

            # Pastikan domain utama adalah Fasih
            if "fasih-sm.bps.go.id" not in url:
                return False

            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            path = parsed.path.lower().rstrip("/")

            # 1. Jika URL masih di domain SSO, Keycloak, OAuth, atau /login
            if any(k in url for k in ["sso.bps.go.id", "oauth2", "keycloak", "realms", "accounts.google"]):
                return False
            if "/auth/login" in path or path.endswith("/login"):
                return False

            # 2. Jika URL persis adalah root login: https://fasih-sm.bps.go.id/app atau https://fasih-sm.bps.go.id
            if path in ["/app", ""]:
                # Pada path /app, jika ada tombol SSO atau teks selamat datang, belum login
                try:
                    if page.locator("text='Lanjutkan dengan SSO'").first.count() > 0:
                        return False
                    if page.locator("text='Selamat Datang Kembali'").first.count() > 0:
                        return False
                except Exception:
                    pass
                return False

            # 3. Pengecekan selector login di DOM
            unauth_selectors = [
                "#kc-form-login",
                "#kc-login",
                "text='Lanjutkan dengan SSO'",
                "text='Selamat Datang Kembali'",
                "a[href*='/auth/login']"
            ]
            for sel in unauth_selectors:
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        return False
                except Exception:
                    pass

            # 4. INDIKATOR UTAMA TERPERCAYA: Jalur pasca-login (berdasarkan PATH, bukan query parameter!)
            # Begitu berhasil login, Fasih SELALU mengarahkan ke /surveys (atau penugasan/monitoring)
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
                # Pengguna sudah berhasil dialihkan ke halaman internal survei/penugasan!
                return True

            # 5. Fallback DOM jika berada di URL subpath lain
            auth_selectors = [
                "a[href*='logout']",
                "button:has-text('Logout')",
                "button:has-text('Keluar')",
                ".fasih-form-sidebar",
                "a:has-text('Survei')",
                "a:has-text('Penugasan')"
            ]
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
