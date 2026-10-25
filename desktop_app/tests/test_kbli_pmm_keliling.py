import unittest
from unittest.mock import MagicMock
from playwright.sync_api import sync_playwright
import os
import sys

# Tambahkan desktop_app ke sys.path
sys.path.insert(0, os.path.abspath("desktop_app"))

from core.browser_manager import BrowserManager
from modules.kbli_pmm.engine import _check_keliling_warning, _process_pmm_characteristics

class TestKbliPmmKeliling(unittest.TestCase):
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

    def _get_base_html(self, with_warning=True, kedai_checked=True):
        warning_snippet = ""
        if with_warning:
            warning_snippet = (
                '<div class="tw:space-y-2 tw:font-bold tw:text-xs tw:text-destructive">'
                '<div class="tw:flex tw:flex-row tw:items-start tw:space-x-2">'
                '<span>Jika R.9a diisi kode 2 (Usaha Keliling), maka R.13c diisi kode 10 (Usaha Keliling)</span>'
                '</div></div>'
            )
        data_checked = 'data-checked=""' if kedai_checked else ''

        return f"""<!DOCTYPE html><html><body>
        <div id="produk_sendiri#1001">
          <div role="radiogroup">
            <div role="group"><input type="radio" value="1"><label>1. Ya</label></div>
            <div role="group"><input type="radio" value="2"><label>2. Tidak</label></div>
          </div>
        </div>
        <div id="layanan_mamin#1001">
          <div role="radiogroup">
            <div role="group"><input type="radio" value="1"><label>1. Ya</label></div>
            <div role="group"><input type="radio" value="2"><label>2. Tidak</label></div>
          </div>
        </div>
        <div id="lokasi_usaha#1001">
          <div role="radiogroup" id="radiogroup-cl-150">
            <div role="group" id="item-5" {data_checked}>
              <input type="radio" name="radiogroup-cl-150" value="05" {data_checked}>
              <div role="radio" {data_checked}></div>
              <label {data_checked}>5.  Kedai, stan, tenda</label>
            </div>
            <div role="group" id="item-10">
              <input type="radio" name="radiogroup-cl-150" value="10">
              <div role="radio"></div>
              <label>10. Keliling</label>
            </div>
          </div>
          <div id="warning-slot">{warning_snippet}</div>
        </div></body></html>"""

    def test_pre_check_warning_selects_keliling(self):
        """Uji saat warning Usaha Keliling sudah ada sebelum eksekusi (misal dari data tersimpan/anomali awal)"""
        html = self._get_base_html(with_warning=True, kedai_checked=True)
        self.page.set_content(html)
        container = self.page.locator("div[id^='lokasi_usaha#']").first

        self.assertTrue(_check_keliling_warning(container, self.page))

        ok, status, ket = _process_pmm_characteristics(self.page, kbli_akhir="56102")
        self.assertTrue(ok)
        self.assertEqual(status, "SUKSES")
        self.assertIn("10. Keliling", ket)

        inp_10 = container.locator("input[value='10']")
        self.assertTrue(inp_10.is_checked())

    def test_post_check_dynamic_warning_corrects_to_keliling(self):
        """Uji saat warning Usaha Keliling muncul secara reaktif setelah opsi Kedai (05) diklik"""
        html = self._get_base_html(with_warning=False, kedai_checked=False)
        self.page.set_content(html)

        # Pasang listener reaktif seperti Fasih: saat 05 diklik, form menampilkan warning
        self.page.evaluate("""() => {
            const inp5 = document.querySelector("input[value='05']");
            const slot = document.getElementById("warning-slot");
            inp5.addEventListener("click", () => {
                slot.innerHTML = '<div class="tw:space-y-2 tw:font-bold tw:text-xs tw:text-destructive"><span>Jika R.9a diisi kode 2 (Usaha Keliling), maka R.13c diisi kode 10 (Usaha Keliling)</span></div>';
            });
        }""")

        container = self.page.locator("div[id^='lokasi_usaha#']").first
        self.assertFalse(_check_keliling_warning(container, self.page))

        ok, status, ket = _process_pmm_characteristics(self.page, kbli_akhir="56102")
        self.assertTrue(ok)
        self.assertEqual(status, "SUKSES")
        self.assertIn("10. Keliling", ket)

        inp_10 = container.locator("input[value='10']")
        self.assertTrue(inp_10.is_checked())


if __name__ == "__main__":
    unittest.main()
