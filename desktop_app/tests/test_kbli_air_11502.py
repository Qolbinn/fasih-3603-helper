import unittest
import os
import sys

# Tambahkan path desktop_app ke sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modules.kbli_air_11502.selectors import (
    KBLI_AIR_11502_SELECTORS,
    KBLI_AIR_11052_SELECTORS,
    EXCEL_KBLI_AIR_11502_COLUMNS_CONFIG,
    EXCEL_KBLI_AIR_11052_COLUMNS_CONFIG
)
from modules.kbli_air_11502.validator import ExcelKBLIAir11502Validator, ExcelKBLIAir11052Validator

class TestKBLIAir11502Scaffold(unittest.TestCase):
    def test_selectors_exist(self):
        """Memverifikasi seluruh selector karakteristik KBLI Air 11502 terdaftar."""
        required_keys = [
            "container_produk_sendiri",
            "container_layanan_mamin",
            "container_input",
            "textarea_input",
            "container_proses",
            "textarea_proses",
            "container_kbli_genai",
            "container_master_kbli",
            "textarea_master_kbli",
            "btn_catatan",
            "btn_kirim",
            "btn_konfirmasi_kirim",
            "dialog_sukses"
        ]
        for key in required_keys:
            self.assertIn(key, KBLI_AIR_11502_SELECTORS, f"Selector {key} harus ada di KBLI_AIR_11502_SELECTORS")
            self.assertIn(key, KBLI_AIR_11052_SELECTORS, f"Selector {key} harus ada di KBLI_AIR_11052_SELECTORS")

    def test_column_config(self):
        """Memverifikasi konfigurasi kolom Excel untuk KBLI Air."""
        self.assertIn("keg_utama", EXCEL_KBLI_AIR_11502_COLUMNS_CONFIG)
        self.assertIn("kbli_akhir", EXCEL_KBLI_AIR_11502_COLUMNS_CONFIG)
        self.assertIn("url", EXCEL_KBLI_AIR_11502_COLUMNS_CONFIG)
        self.assertIn("status_kbli", EXCEL_KBLI_AIR_11502_COLUMNS_CONFIG)
        self.assertIn("kbli_terbaru", EXCEL_KBLI_AIR_11502_COLUMNS_CONFIG)

    def test_validator_alias(self):
        """Memverifikasi alias class validator 11052 dan 11502 merujuk pada class yang sama."""
        self.assertEqual(ExcelKBLIAir11052Validator, ExcelKBLIAir11502Validator)

if __name__ == "__main__":
    unittest.main()

