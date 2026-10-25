import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Pastikan root direktori desktop_app berada dalam sys.path
DESKTOP_APP_DIR = Path(__file__).resolve().parent.parent
if str(DESKTOP_APP_DIR) not in sys.path:
    sys.path.insert(0, str(DESKTOP_APP_DIR))

import config
from core.browser_manager import BrowserManager
from core.window_controller import WindowController
from core.event_bus import EventBus

# Import all 7 engines
from modules.cleaning_usaha.engine import DataCleaningEngine
from modules.remark_kbli.engine import RemarkKBLIEngine
from modules.kbli_sembako.engine import KBLISembakoEngine
from modules.kbli_pmm.engine import KBLIPMMEngine
from modules.cleaning_nik_r30.engine import CleaningNIKEngine
from modules.cleaning_nik_r29.engine import CleaningNIKR29Engine
from modules.cleaning_nik_r27.engine import CleaningNIKR27Engine


class TestBrowserConfiguration(unittest.TestCase):
    """Pengujian konfigurasi dasar konstanta dan port isolasi multi-browser."""

    def test_browser_constants(self):
        self.assertEqual(config.BROWSER_CHROME, "chrome")
        self.assertEqual(config.BROWSER_EDGE, "edge")

    def test_distinct_ports(self):
        """Chrome dan Edge harus memiliki port CDP terpisah untuk mencegah konflik binding."""
        self.assertEqual(config.CHROME_CDP_PORT, 9222)
        self.assertEqual(config.EDGE_CDP_PORT, 9223)
        self.assertNotEqual(config.CHROME_CDP_PORT, config.EDGE_CDP_PORT)

    def test_distinct_profile_directories(self):
        """Direktori profil Chrome dan Edge harus berbeda agar session & cookies terisolasi."""
        self.assertNotEqual(config.CHROME_PROFILE_DIR, config.EDGE_PROFILE_DIR)
        self.assertTrue(str(config.EDGE_PROFILE_DIR).endswith("edge_profile"))
        self.assertTrue(str(config.CHROME_PROFILE_DIR).endswith("chrome_profile"))


class TestSettingsPersistence(unittest.TestCase):
    """Pengujian pembacaan dan penyimpanan pengaturan browser (Chrome/Edge/Incognito)."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_settings_file = config.SETTINGS_FILE
        config.SETTINGS_FILE = Path(self.test_dir) / "test_settings.json"
        BrowserManager._cached_settings = None

    def tearDown(self):
        config.SETTINGS_FILE = self.orig_settings_file
        BrowserManager._cached_settings = None
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_settings_when_file_missing(self):
        """Saat settings.json belum ada, harus kembali ke default (chrome, non-incognito)."""
        settings = BrowserManager.load_settings(force_reload=True)
        self.assertEqual(settings.get("active_browser"), config.BROWSER_CHROME)
        self.assertFalse(settings.get("incognito", False))
        self.assertEqual(BrowserManager.get_active_browser(), config.BROWSER_CHROME)
        self.assertFalse(BrowserManager.is_incognito_active())

    def test_save_and_load_edge_selection(self):
        """Pengalihan ke Edge harus tersimpan ke file dan terbaca kembali."""
        BrowserManager.set_active_browser(config.BROWSER_EDGE)
        self.assertEqual(BrowserManager.get_active_browser(), config.BROWSER_EDGE)

        # Verifikasi konten file di disk
        self.assertTrue(config.SETTINGS_FILE.exists())
        with open(config.SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("active_browser"), config.BROWSER_EDGE)

    def test_save_and_load_incognito_toggle(self):
        """Toggle incognito harus tersimpan ke disk dan mematuhi feature flag ENABLE_INCOGNITO_MODE."""
        # 1. Saat ENABLE_INCOGNITO_MODE dinonaktifkan (default saat ini)
        config.ENABLE_INCOGNITO_MODE = False
        BrowserManager.set_incognito(True)
        self.assertFalse(BrowserManager.is_incognito_active(), "Saat flag false, is_incognito_active harus selalu False")

        # 2. Saat ENABLE_INCOGNITO_MODE diaktifkan kembali
        config.ENABLE_INCOGNITO_MODE = True
        BrowserManager.set_incognito(True)
        self.assertTrue(BrowserManager.is_incognito_active())

        BrowserManager.set_incognito(False)
        self.assertFalse(BrowserManager.is_incognito_active())
        config.ENABLE_INCOGNITO_MODE = False  # Kembalikan ke state awal

    def test_corrupted_settings_file_recovery(self):
        """File settings.json rusak/korup harus ditangani dengan aman tanpa crash."""
        with open(config.SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON DATA %%%")

        settings = BrowserManager.load_settings(force_reload=True)
        self.assertEqual(settings.get("active_browser"), config.BROWSER_CHROME)
        self.assertEqual(BrowserManager.get_active_browser(), config.BROWSER_CHROME)


class TestBrowserManagerDynamicMapping(unittest.TestCase):
    """Pengujian pemetaan dinamis port, URL, dan direktori profil berdasarkan browser."""

    def test_cdp_port_resolution(self):
        self.assertEqual(BrowserManager.get_cdp_port(config.BROWSER_CHROME), 9222)
        self.assertEqual(BrowserManager.get_cdp_port(config.BROWSER_EDGE), 9223)
        # Fallback untuk nilai input tak dikenal
        self.assertEqual(BrowserManager.get_cdp_port("unknown_browser"), 9222)

    def test_cdp_url_resolution(self):
        self.assertEqual(BrowserManager.get_cdp_url(config.BROWSER_CHROME), "http://127.0.0.1:9222")
        self.assertEqual(BrowserManager.get_cdp_url(config.BROWSER_EDGE), "http://127.0.0.1:9223")

    def test_profile_dir_resolution(self):
        self.assertEqual(BrowserManager.get_profile_dir(config.BROWSER_CHROME), config.CHROME_PROFILE_DIR)
        self.assertEqual(BrowserManager.get_profile_dir(config.BROWSER_EDGE), config.EDGE_PROFILE_DIR)

    def test_browser_executable_path_detection(self):
        """Memeriksa apakah jalur deteksi biner browser mengembalikan string atau None secara aman."""
        chrome_path = BrowserManager.get_browser_path(config.BROWSER_CHROME)
        edge_path = BrowserManager.get_browser_path(config.BROWSER_EDGE)

        # Setidaknya salah satu atau keduanya ada di sistem Windows
        if chrome_path:
            self.assertTrue(Path(chrome_path).exists(), f"Jalur Chrome tidak valid: {chrome_path}")
        if edge_path:
            self.assertTrue(Path(edge_path).exists(), f"Jalur Edge tidak valid: {edge_path}")


class TestCacheClearLogic(unittest.TestCase):
    """Pengujian logika pembersihan cache profil browser."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.mock_profile = Path(self.test_dir) / "test_profile"
        self.mock_profile.mkdir(parents=True, exist_ok=True)

        # Buat struktur file dummy di profil
        dummy_dir = self.mock_profile / "Default" / "Cache"
        dummy_dir.mkdir(parents=True, exist_ok=True)
        (dummy_dir / "data_0").write_text("dummy cache data", encoding="utf-8")

        # Monkey-patch get_profile_dir
        self.orig_get_profile = BrowserManager.get_profile_dir
        BrowserManager.get_profile_dir = lambda b_type: self.mock_profile

    def tearDown(self):
        BrowserManager.get_profile_dir = self.orig_get_profile
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_clear_browser_cache_cleans_targets(self):
        ok, msg = BrowserManager.clear_browser_cache(config.BROWSER_CHROME)
        self.assertTrue(ok)
        self.assertIn("berhasil", msg.lower())


class TestWindowControllerMultiBrowser(unittest.TestCase):
    """Pengujian deteksi PID CDP di WindowController untuk Chrome dan Edge."""

    def test_get_cdp_pids_runs_cleanly(self):
        """Memastikan fungsi get_cdp_pids dapat dipanggil tanpa error sintaks/runtime."""
        pids = WindowController.get_cdp_pids()
        self.assertIsInstance(pids, (list, set))


class TestEngineMultiBrowserCompatibility(unittest.TestCase):
    """Pengujian kompatibilitas semua 7 modul engine dengan multi-browser parameter."""

    def setUp(self):
        self.event_bus = EventBus()
        self.test_excel = "dummy_excel.xlsx"

    def _verify_engine_config(self, engine, expected_browser, expected_port, expected_incognito):
        self.assertEqual(engine.browser_type, expected_browser)
        self.assertEqual(engine.cdp_url, f"http://127.0.0.1:{expected_port}")
        self.assertEqual(engine.incognito, expected_incognito)

    def test_all_seven_engines_with_edge_and_incognito(self):
        """Verifikasi bahwa ke-7 engine mendukung konfigurasi Edge + Incognito."""
        opts = {
            "browser_type": config.BROWSER_EDGE,
            "incognito": True,
            "cdp_url": "http://127.0.0.1:9223"
        }

        engines = [
            ("cleaning_usaha", DataCleaningEngine(self.test_excel, self.event_bus, opts)),
            ("remark_kbli", RemarkKBLIEngine(self.test_excel, self.event_bus, opts)),
            ("kbli_sembako", KBLISembakoEngine(self.test_excel, self.event_bus, opts)),
            ("kbli_pmm", KBLIPMMEngine(self.test_excel, self.event_bus, opts)),
            ("cleaning_nik_r30", CleaningNIKEngine(self.test_excel, self.event_bus, opts)),
            ("cleaning_nik_r29", CleaningNIKR29Engine(self.test_excel, self.event_bus, opts)),
            ("cleaning_nik_r27", CleaningNIKR27Engine(self.test_excel, self.event_bus, opts)),
        ]

        for mod_name, engine in engines:
            with self.subTest(module=mod_name):
                self._verify_engine_config(engine, config.BROWSER_EDGE, 9223, True)

    def test_all_seven_engines_with_chrome_default(self):
        """Verifikasi bahwa ke-7 engine mendukung konfigurasi Chrome + Non-Incognito."""
        opts = {
            "browser_type": config.BROWSER_CHROME,
            "incognito": False,
            "cdp_url": "http://127.0.0.1:9222"
        }

        engines = [
            ("cleaning_usaha", DataCleaningEngine(self.test_excel, self.event_bus, opts)),
            ("remark_kbli", RemarkKBLIEngine(self.test_excel, self.event_bus, opts)),
            ("kbli_sembako", KBLISembakoEngine(self.test_excel, self.event_bus, opts)),
            ("kbli_pmm", KBLIPMMEngine(self.test_excel, self.event_bus, opts)),
            ("cleaning_nik_r30", CleaningNIKEngine(self.test_excel, self.event_bus, opts)),
            ("cleaning_nik_r29", CleaningNIKR29Engine(self.test_excel, self.event_bus, opts)),
            ("cleaning_nik_r27", CleaningNIKR27Engine(self.test_excel, self.event_bus, opts)),
        ]

        for mod_name, engine in engines:
            with self.subTest(module=mod_name):
                self._verify_engine_config(engine, config.BROWSER_CHROME, 9222, False)

    def test_custom_cdp_url_override(self):
        """Engine harus mengutamakan custom cdp_url jika secara eksplisit diberikan."""
        custom_url = "http://127.0.0.1:9999"
        opts = {"cdp_url": custom_url}
        engine = DataCleaningEngine(self.test_excel, self.event_bus, opts)
        self.assertEqual(engine.cdp_url, custom_url)


class TestBrowserPortAvailabilityProbe(unittest.TestCase):
    """Pengujian probe status CDP pada port non-aktif."""

    def test_is_cdp_running_on_closed_port(self):
        """Probe pada port yang sedang tertutup harus mengembalikan (False, None) dengan cepat."""
        is_running, b_name = BrowserManager.is_cdp_running(port=59876, timeout=0.2)
        self.assertFalse(is_running)
        self.assertIsNone(b_name)


class TestLaunchFlagsBuilder(unittest.TestCase):
    """Pengujian penyusunan argumen command-line peluncuran browser."""

    def test_chrome_normal_flags(self):
        flags = BrowserManager.build_launch_flags(config.BROWSER_CHROME, incognito=False)
        self.assertTrue(any("--remote-debugging-port=9222" in f for f in flags))
        self.assertTrue(any("--user-data-dir=" in f and "chrome_profile" in f for f in flags))
        self.assertFalse(any("--incognito" in f for f in flags))

    def test_chrome_incognito_flags(self):
        flags = BrowserManager.build_launch_flags(config.BROWSER_CHROME, incognito=True)
        self.assertTrue(any("--remote-debugging-port=9222" in f for f in flags))
        self.assertTrue(any("--incognito" in f for f in flags))

    def test_edge_normal_flags(self):
        flags = BrowserManager.build_launch_flags(config.BROWSER_EDGE, incognito=False)
        self.assertTrue(any("--remote-debugging-port=9223" in f for f in flags))
        self.assertTrue(any("--user-data-dir=" in f and "edge_profile" in f for f in flags))
        self.assertFalse(any("-inprivate" in f for f in flags))

    def test_edge_inprivate_flags(self):
        flags = BrowserManager.build_launch_flags(config.BROWSER_EDGE, incognito=True)
        self.assertTrue(any("--remote-debugging-port=9223" in f for f in flags))
        self.assertTrue(any("-inprivate" in f for f in flags))


class TestCacheClearSafetyWhenActive(unittest.TestCase):
    """Pengujian pengamanan agar pembersihan cache ditolak saat browser masih berjalan."""

    def setUp(self):
        self.orig_is_running = BrowserManager.is_cdp_running

    def tearDown(self):
        BrowserManager.is_cdp_running = self.orig_is_running

    def test_refuse_clear_when_browser_running(self):
        # Simulasikan browser sedang aktif
        BrowserManager.is_cdp_running = lambda browser_type=None, port=None, timeout=1.5: (True, "MockChromium")
        ok, msg = BrowserManager.clear_browser_cache(config.BROWSER_CHROME)
        self.assertFalse(ok, "Pembersihan cache harus ditolak jika browser sedang aktif!")
        self.assertIn("tutup jendela browser", msg.lower())


class TestBrowserManagerSwitchAndEngineDefaults(unittest.TestCase):
    """Pengujian pengalihan active_browser di BrowserManager dan pewarisannya ke engine tanpa argumen."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_settings_file = config.SETTINGS_FILE
        config.SETTINGS_FILE = Path(self.test_dir) / "test_settings.json"
        BrowserManager._cached_settings = None

    def tearDown(self):
        config.SETTINGS_FILE = self.orig_settings_file
        BrowserManager._cached_settings = None
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_engine_inherits_switched_edge_browser(self):
        """Saat user berpindah ke Edge, engine tanpa argumen eksplisit harus otomatis terhubung ke Edge port 9223."""
        BrowserManager.set_active_browser(config.BROWSER_EDGE)
        BrowserManager.set_incognito(True)

        # 1. Saat ENABLE_INCOGNITO_MODE False (default saat ini)
        config.ENABLE_INCOGNITO_MODE = False
        engine = DataCleaningEngine("dummy.xlsx", EventBus(), config_options={})
        self.assertEqual(engine.browser_type, config.BROWSER_EDGE)
        self.assertEqual(engine.cdp_url, "http://127.0.0.1:9223")
        self.assertFalse(engine.incognito)

        # 2. Saat ENABLE_INCOGNITO_MODE True
        config.ENABLE_INCOGNITO_MODE = True
        engine_incog = DataCleaningEngine("dummy.xlsx", EventBus(), config_options={})
        self.assertTrue(engine_incog.incognito)
        config.ENABLE_INCOGNITO_MODE = False


if __name__ == "__main__":
    unittest.main(verbosity=2)
