import unittest
from playwright.sync_api import sync_playwright
import os
import sys

# Tambahkan path desktop_app ke sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.browser_manager import BrowserManager
from modules.kbli_kategori_A.engine import _process_a_characteristics, is_kegiatan_jasa
from modules.kbli_kategori_A.validator import ExcelKBLIKategoriAValidator
from modules.kbli_kategori_A.selectors import KBLI_KATEGORI_A_SELECTORS

class TestKBLIKategoriA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chrome_path = BrowserManager.get_browser_path("chrome")
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=cls.chrome_path,
            headless=True
        )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page()

    def tearDown(self):
        self.page.close()

    def test_is_kegiatan_jasa_rules(self):
        """Memverifikasi bahwa kata 'jasa' pada semua contoh user dideteksi dengan tepat."""
        jasa_examples = [
            "JASA PENGGILINGAN PADI",
            "Jasa air taman atau menyiram tanaman taman",
            "JASA PEMOTONGAN POHON DAN JUAL KAYU",
            "JASA PENEBANGAN POHON",
            "Jasa angkut hasil pertanian",
            "Jasa tanam benih padi",
            "Jasa penyewaan traktor",
            "JASA PENYEDIAAN TEMPAT PEMANCINGAN IKAN",
            "Usaha jasa panen padi",
            "JASA-PENGOLAHAN LAHAN"
        ]
        for ex in jasa_examples:
            self.assertTrue(is_kegiatan_jasa(ex), f"Harus terdeteksi sebagai Jasa: '{ex}'")

        non_jasa_examples = [
            "Pertanian Padi Sawah",
            "Perkebunan Kelapa Sawit",
            "Budidaya Ikan Lele",
            "Peternakan Ayam Broiler",
            "Penebangan Kayu Hutan",
            "Perikanan Tangkap Laut"
        ]
        for ex in non_jasa_examples:
            self.assertFalse(is_kegiatan_jasa(ex), f"TIDAK boleh terdeteksi sebagai Jasa: '{ex}'")

    def _get_html(self):
        return """<!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body>
            <!-- 1. Produksi Barang Sendiri (13. b1) -->
            <div id="produk_sendiri#1002">
                <div role="radiogroup">
                    <div role="group">
                        <input type="radio" name="rg1" value="1" id="r1_1">
                        <div role="radio"></div>
                        <label for="r1_1">1. Ya</label>
                    </div>
                    <div role="group">
                        <input type="radio" name="rg1" value="2" id="r1_2">
                        <div role="radio"></div>
                        <label for="r1_2">2. Tidak</label>
                    </div>
                </div>
            </div>

            <!-- 2. Layanan Makan Minum (13. b2) -->
            <div id="layanan_mamin#1002">
                <div role="radiogroup">
                    <div role="group">
                        <input type="radio" name="rg2" value="1" id="r2_1">
                        <div role="radio"></div>
                        <label for="r2_1">1. Ya</label>
                    </div>
                    <div role="group">
                        <input type="radio" name="rg2" value="2" id="r2_2">
                        <div role="radio"></div>
                        <label for="r2_2">2. Tidak</label>
                    </div>
                </div>
            </div>

            <!-- 3. Penjualan Barang (13. b3) -->
            <div id="keg_penjualan#1002">
                <div role="radiogroup">
                    <div role="group">
                        <input type="radio" name="rg3" value="1" id="r3_1">
                        <div role="radio"></div>
                        <label for="r3_1">1. Ya</label>
                    </div>
                    <div role="group">
                        <input type="radio" name="rg3" value="2" id="r3_2">
                        <div role="radio"></div>
                        <label for="r3_2">2. Tidak</label>
                    </div>
                </div>
            </div>

            <!-- 4. Aktivitas yang Dilakukan (13. b4) -->
            <div id="keg_jasa#1002">
                <div role="radiogroup">
                    <div role="group">
                        <input type="radio" name="rg4" value="1" id="r4_1">
                        <div role="radio"></div>
                        <label for="r4_1">1. Jasa</label>
                    </div>
                    <div role="group">
                        <input type="radio" name="rg4" value="2" id="r4_2">
                        <div role="radio"></div>
                        <label for="r4_2">2. Pertanian, Perikanan, dan Kehutanan</label>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def test_process_a_non_jasa_flow(self):
        """Memverifikasi flow KBLI Kategori A Non-Jasa: 13.b4 memilih 2. Pertanian, Perikanan, dan Kehutanan."""
        self.page.set_content(self._get_html())

        ok, status, ket = _process_a_characteristics(self.page, keg_utama="PERTANIAN PADI SAWAH")
        self.assertTrue(ok)
        self.assertEqual(status, "SUKSES")

        # Verifikasi bahwa radio value='2' pada keempat rincian sudah terpilih
        r1_val = self.page.locator("div[id^='produk_sendiri'] input[value='2']").is_checked()
        r2_val = self.page.locator("div[id^='layanan_mamin'] input[value='2']").is_checked()
        r3_val = self.page.locator("div[id^='keg_penjualan'] input[value='2']").is_checked()
        r4_val = self.page.locator("div[id^='keg_jasa'] input[value='2']").is_checked()

        self.assertTrue(r1_val, "Rincian 13.b1 harus terpilih value=2 (Tidak)")
        self.assertTrue(r2_val, "Rincian 13.b2 harus terpilih value=2 (Tidak)")
        self.assertTrue(r3_val, "Rincian 13.b3 harus terpilih value=2 (Tidak)")
        self.assertTrue(r4_val, "Rincian 13.b4 harus terpilih value=2 (Pertanian, Perikanan, dan Kehutanan)")

    def test_process_a_jasa_flow(self):
        """Memverifikasi flow KBLI Kategori A Jasa: 13.b4 memilih 1. Jasa."""
        self.page.set_content(self._get_html())

        ok, status, ket = _process_a_characteristics(self.page, keg_utama="JASA PENGGILINGAN PADI")
        self.assertTrue(ok)
        self.assertEqual(status, "SUKSES")

        # Verifikasi bahwa 13.b1, 13.b2, 13.b3 tetap Tidak (value=2), dan 13.b4 memilih Jasa (value=1)
        r1_val = self.page.locator("div[id^='produk_sendiri'] input[value='2']").is_checked()
        r2_val = self.page.locator("div[id^='layanan_mamin'] input[value='2']").is_checked()
        r3_val = self.page.locator("div[id^='keg_penjualan'] input[value='2']").is_checked()
        r4_val = self.page.locator("div[id^='keg_jasa'] input[value='1']").is_checked()

        self.assertTrue(r1_val, "Rincian 13.b1 harus terpilih value=2 (Tidak)")
        self.assertTrue(r2_val, "Rincian 13.b2 harus terpilih value=2 (Tidak)")
        self.assertTrue(r3_val, "Rincian 13.b3 harus terpilih value=2 (Tidak)")
        self.assertTrue(r4_val, "Rincian 13.b4 harus terpilih value=1 (1. Jasa)")

if __name__ == "__main__":
    unittest.main()
