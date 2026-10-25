import os
import sys
import json
import time
import shutil
import subprocess
import urllib.request
from urllib.parse import urlparse
from pathlib import Path
from config import (
    CHROME_PATHS, EDGE_PATHS, CHROME_CANDIDATE_PATHS,
    CHROME_PROFILE_DIR, EDGE_PROFILE_DIR,
    CHROME_CDP_PORT, EDGE_CDP_PORT, DEFAULT_CDP_PORT, DEFAULT_CDP_HOST,
    CDP_URL, BROWSER_CHROME, BROWSER_EDGE, DEFAULT_BROWSER,
    SETTINGS_FILE, BASE_BROWSER_FLAGS
)
import config
from core.logger import logger

class BrowserManager:
    _cached_settings = None

    @classmethod
    def load_settings(cls, force_reload=False):
        """Memuat preferensi pengaturan browser dari settings.json."""
        if not force_reload and cls._cached_settings is not None:
            return cls._cached_settings

        default_settings = {
            "selected_browser": config.DEFAULT_BROWSER,
            "active_browser": config.DEFAULT_BROWSER,
            "incognito": False
        }

        if config.SETTINGS_FILE.exists():
            try:
                with open(config.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        default_settings.update(data)
                        if "selected_browser" in data and "active_browser" not in data:
                            default_settings["active_browser"] = data["selected_browser"]
                        elif "active_browser" in data and "selected_browser" not in data:
                            default_settings["selected_browser"] = data["active_browser"]
            except Exception as e:
                logger.warning(f"Gagal membaca settings.json: {e}")

        cls._cached_settings = default_settings
        return cls._cached_settings

    @classmethod
    def save_settings(cls, new_settings):
        """Menyimpan preferensi pengaturan browser ke settings.json."""
        current = cls.load_settings()
        current.update(new_settings)
        if "selected_browser" in new_settings and "active_browser" not in new_settings:
            current["active_browser"] = new_settings["selected_browser"]
        elif "active_browser" in new_settings and "selected_browser" not in new_settings:
            current["selected_browser"] = new_settings["active_browser"]
        cls._cached_settings = current
        try:
            config.SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(config.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
        except Exception as e:
            logger.warning(f"Gagal menyimpan settings.json: {e}")

    @classmethod
    def get_active_browser(cls):
        """Mengembalikan browser aktif yang dipilih ('chrome' atau 'edge')."""
        s = cls.load_settings()
        return s.get("selected_browser") or s.get("active_browser") or config.DEFAULT_BROWSER

    @classmethod
    def set_active_browser(cls, browser_type):
        """Menyetel browser aktif ('chrome' atau 'edge')."""
        b = str(browser_type).lower().strip()
        if b in [config.BROWSER_CHROME, config.BROWSER_EDGE]:
            cls.save_settings({"selected_browser": b, "active_browser": b})
            logger.info(f"Browser aktif diubah ke: {b.upper()}")

    @classmethod
    def is_incognito_active(cls):
        """Memeriksa apakah mode Incognito / InPrivate diaktifkan."""
        if not getattr(config, "ENABLE_INCOGNITO_MODE", True):
            return False
        return bool(cls.load_settings().get("incognito", False))

    @classmethod
    def set_incognito(cls, active: bool):
        """Mengaktifkan atau menonaktifkan mode Incognito."""
        cls.save_settings({"incognito": bool(active)})
        mode_str = "AKTIF" if active else "NONAKTIF"
        logger.info(f"Mode Incognito/InPrivate disetel ke: {mode_str}")

    @classmethod
    def get_browser_path(cls, browser_type=None):
        """Mencari lokasi file eksekusi browser yang dipilih di sistem Windows."""
        b_type = (browser_type or cls.get_active_browser()).lower()
        candidates = CHROME_PATHS if b_type == BROWSER_CHROME else EDGE_PATHS
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        # Fallback pencarian sekunder
        fallback_candidates = EDGE_PATHS if b_type == BROWSER_CHROME else CHROME_PATHS
        for candidate in fallback_candidates:
            if candidate.exists():
                return str(candidate)
        return None

    @staticmethod
    def get_installed_browser_path():
        """Metode legacy untuk kompatibilitas ke belakang."""
        return BrowserManager.get_browser_path(BrowserManager.get_active_browser())

    @classmethod
    def get_cdp_port(cls, browser_type=None):
        """Mengembalikan port remote debugging CDP untuk browser yang dipilih."""
        b_type = (browser_type or cls.get_active_browser()).lower().strip()
        return EDGE_CDP_PORT if b_type == BROWSER_EDGE else CHROME_CDP_PORT

    @classmethod
    def get_cdp_url(cls, browser_type=None):
        """Mengembalikan URL CDP endpoint untuk koneksi Playwright."""
        port = cls.get_cdp_port(browser_type)
        return f"http://{DEFAULT_CDP_HOST}:{port}"

    @classmethod
    def get_profile_dir(cls, browser_type=None):
        """Mengembalikan folder profil pengguna terisolasi untuk browser."""
        b_type = (browser_type or cls.get_active_browser()).lower().strip()
        return EDGE_PROFILE_DIR if b_type == BROWSER_EDGE else CHROME_PROFILE_DIR

    @classmethod
    def is_cdp_running(cls, browser_type=None, port=None, timeout=1.5):
        """Memeriksa apakah port debugging browser aktif."""
        target_port = port or cls.get_cdp_port(browser_type)
        try:
            url = f"http://{DEFAULT_CDP_HOST}:{target_port}/json/version"
            req = urllib.request.Request(url, headers={"User-Agent": "Playwright"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                return True, data.get("Browser", "Chromium")
        except Exception:
            return False, None

    @classmethod
    def build_launch_flags(cls, browser_type=None, incognito=None):
        """Menyusun daftar flags / argumen command-line untuk peluncuran browser."""
        b_type = (browser_type or cls.get_active_browser()).lower().strip()
        is_incog = cls.is_incognito_active() if incognito is None else bool(incognito)
        port = cls.get_cdp_port(b_type)
        profile_dir = cls.get_profile_dir(b_type)

        flags = [f"--remote-debugging-port={port}"] + BASE_BROWSER_FLAGS.copy()
        if is_incog:
            flags.append("--incognito" if b_type == BROWSER_CHROME else "-inprivate")
        else:
            flags.append(f"--user-data-dir={str(profile_dir)}")
        return flags

    @classmethod
    def launch_browser(cls, browser_type=None, incognito=None, target_url="https://fasih-sm.bps.go.id/app"):
        """Meluncurkan browser (Chrome / Edge) dengan port CDP dan profil terisolasi."""
        from core.window_controller import WindowController

        b_type = (browser_type or cls.get_active_browser()).lower()
        is_incog = cls.is_incognito_active() if incognito is None else bool(incognito)
        port = cls.get_cdp_port(b_type)

        is_running, name = cls.is_cdp_running(browser_type=b_type, port=port)
        if is_running:
            logger.info(f"Browser {b_type.upper()} sudah aktif di port {port} ({name}). Memfokuskan jendela...")
            WindowController.restore_and_focus_browser()
            return True, f"Browser {b_type.upper()} sudah aktif ({name})"

        browser_exe = cls.get_browser_path(b_type)
        if not browser_exe:
            logger.error(f"Tidak ditemukan instalasi browser {b_type.upper()} di lokasi standar!")
            return False, f"Browser {b_type.upper()} tidak ditemukan di laptop ini."

        logger.info(f"Meluncurkan browser: {Path(browser_exe).name} (Mode: {'Incognito' if is_incog else 'Normal'}, Port: {port})...")

        # Susun flags peluncuran browser menggunakan build_launch_flags
        flags = cls.build_launch_flags(browser_type=b_type, incognito=is_incog)

        try:
            if sys.platform == "win32":
                flags_str = " ".join(f'"{f}"' if " " in f else f for f in flags)
                cmd_line = f'start "" "{browser_exe}" {flags_str} "{target_url}"'
                subprocess.Popen(cmd_line, shell=True)
            else:
                subprocess.Popen([browser_exe] + flags + [target_url])

            # Tunggu port terbuka hingga 12 detik
            for _ in range(24):
                time.sleep(0.5)
                active, b_name = cls.is_cdp_running(browser_type=b_type, port=port)
                if active:
                    logger.success(f"Browser {b_type.upper()} berhasil diluncurkan & terhubung di port {port} ({b_name}).")
                    time.sleep(0.5)
                    WindowController.restore_and_focus_browser()
                    return True, f"Berhasil membuka {b_type.upper()}"

            return False, f"Browser {b_type.upper()} diluncurkan tetapi port {port} belum merespons."
        except Exception as e:
            logger.error(f"Gagal meluncurkan browser: {e}")
            return False, str(e)

    @classmethod
    def ensure_browser_ready(cls, browser_type=None, incognito=None, target_url="https://fasih-sm.bps.go.id/app"):
        """Memastikan browser yang dipilih sudah aktif; jika belum, otomatis meluncurkannya."""
        b_type = (browser_type or cls.get_active_browser()).lower()
        port = cls.get_cdp_port(b_type)
        is_running, name = cls.is_cdp_running(browser_type=b_type, port=port)
        if is_running:
            from core.window_controller import WindowController
            WindowController.restore_and_focus_browser()
            return True, f"Browser {b_type.upper()} sudah aktif ({name})"
        return cls.launch_browser(browser_type=b_type, incognito=incognito, target_url=target_url)

    @classmethod
    def clear_browser_cache(cls, browser_type=None):
        """
        Membersihkan cache dan profil data browser yang dipilih.
        Jika browser sedang berjalan, mewajibkan untuk menutup browser terlebih dahulu.
        """
        b_type = (browser_type or cls.get_active_browser()).lower()
        port = cls.get_cdp_port(b_type)
        is_running, _ = cls.is_cdp_running(browser_type=b_type, port=port, timeout=0.8)
        if is_running:
            return False, f"Browser {b_type.upper()} sedang aktif di port {port}! Harap tutup jendela browser tersebut sebelum membersihkan cache."

        profile_dir = cls.get_profile_dir(b_type)
        if not profile_dir.exists():
            profile_dir.mkdir(parents=True, exist_ok=True)
            return True, f"Profil {b_type.upper()} sudah dalam kondisi bersih."

        errors = []
        for item in profile_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=False)
                else:
                    item.unlink(missing_ok=True)
            except Exception as e:
                errors.append(f"{item.name}: {e}")

        if errors:
            logger.warning(f"Sebagian berkas cache {b_type.upper()} terkunci: {errors[:2]}")
            return True, f"Sebagian besar cache profil {b_type.upper()} berhasil dibersihkan."
        return True, f"Cache dan profil {b_type.upper()} berhasil dibersihkan total."

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

