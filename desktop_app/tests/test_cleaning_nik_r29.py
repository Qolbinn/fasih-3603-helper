import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import openpyxl

from modules.cleaning_nik_r29.selectors import EXCEL_NIK_R29_COLUMNS_CONFIG
from modules.cleaning_nik_r29.validator import ExcelNIKR29Validator
from modules.cleaning_nik_r29.engine import (
    clean_nik_str,
    clean_id_str,
    clean_matched_str,
    parse_nik_length,
    _find_and_open_matching_art,
    _process_nik_r29_cleaning
)

class TestCleaningNIKR29(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("d:/3603 BPS Kab Tangerang/2026/Sensus Ekonomi/Anomali/Fasih 3603 Helper/desktop_app/tests/temp")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.test_excel = self.test_dir / "test_cleaning_nik_r29.xlsx"

    def tearDown(self):
        if self.test_excel.exists():
            try:
                os.remove(self.test_excel)
            except Exception:
                pass

    def test_clean_helpers(self):
        self.assertEqual(clean_nik_str("3603010101900001.0"), "3603010101900001")
        self.assertEqual(clean_nik_str(" 3603-0101-0190-0001 "), "3603010101900001")
        self.assertEqual(clean_id_str("1.0"), "1")
        self.assertEqual(clean_id_str(None), "")
        self.assertEqual(clean_matched_str("7777.0"), "7777")
        self.assertEqual(clean_matched_str("None"), "")
        self.assertEqual(clean_matched_str("nan"), "")
        self.assertEqual(clean_matched_str("-"), "")
        self.assertEqual(clean_matched_str("3603014101920009.0"), "3603014101920009")
        self.assertEqual(parse_nik_length("16.0"), 16)
        self.assertEqual(parse_nik_length("8"), 8)
        self.assertIsNone(parse_nik_length("invalid"))

    def test_validator_template_generation_and_validation(self):
        res_gen = ExcelNIKR29Validator.generate_template_excel(str(self.test_excel))
        self.assertTrue(res_gen)
        self.assertTrue(self.test_excel.exists())

        res_val = ExcelNIKR29Validator.validate_excel_file(str(self.test_excel))
        self.assertTrue(res_val["valid"])
        self.assertEqual(res_val["total_rows"], 4)
        self.assertEqual(len(res_val["rows_data"]), 4)

        row1 = res_val["rows_data"][0]
        self.assertEqual(row1["no_urut_kk"], "1")
        self.assertEqual(row1["nama_dtsen"], "AHMAD SUDIRMAN")
        self.assertEqual(row1["nik_dtsen"], "3603010101900001")
        self.assertEqual(row1["nik_length"], "16")
        self.assertEqual(row1["matched"], "")

    def test_validator_missing_column(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        # Header tanpa 'matched'
        ws.append(["no_urut_kk", "nama_dtsen", "nik_dtsen", "nik_length", "url"])
        ws.append(["1", "BUDI", "3603010101900001", "16", "https://fasih-sm.bps.go.id/penugasan/detail/1"])
        wb.save(self.test_excel)
        wb.close()

        res_val = ExcelNIKR29Validator.validate_excel_file(str(self.test_excel))
        self.assertFalse(res_val["valid"])
        self.assertIn("matched", res_val["error"])

    def test_find_and_open_matching_art_logic(self):
        # Mock Playwright page & locators
        page = MagicMock()
        # Mock Blok I already expanded
        page.locator.return_value.count.return_value = 1
        page.locator.return_value.first.wait_for.return_value = None

        mock_art_1 = MagicMock()
        mock_art_1.get_attribute.return_value = "BUDI SANTOSO"
        mock_art_1.inner_text.return_value = "BUDI SANTOSO"

        mock_art_2 = MagicMock()
        mock_art_2.get_attribute.return_value = "SITI AMINAH"
        mock_art_2.inner_text.return_value = "SITI AMINAH"

        mock_art_3 = MagicMock()
        mock_art_3.get_attribute.return_value = "AHMAD SUDIRMAN"
        mock_art_3.inner_text.return_value = "AHMAD SUDIRMAN"

        # Patch _get_valid_art_items to return 3 family members
        with patch("modules.cleaning_nik_r29.engine._get_valid_art_items") as mock_get_items, \
             patch("modules.cleaning_nik_r29.engine.safe_click") as mock_safe_click:
            mock_get_items.return_value = [
                (mock_art_1, "BUDI SANTOSO"),
                (mock_art_2, "SITI AMINAH"),
                (mock_art_3, "AHMAD SUDIRMAN")
            ]

            # Case 1: Nama ketemu dan no_urut_kk cocok (SITI AMINAH urutan ke-2)
            ok, name, err = _find_and_open_matching_art(page, excel_nama="Siti Aminah", excel_no_urut="2")
            self.assertTrue(ok)
            self.assertEqual(name, "SITI AMINAH")
            self.assertIsNone(err)

            # Case 2: Nama ketemu tapi urutan di Excel salah (SITI AMINAH urutan ke-1 di Excel)
            ok, name, err = _find_and_open_matching_art(page, excel_nama="Siti Aminah", excel_no_urut="1")
            self.assertFalse(ok)
            self.assertIsNone(name)
            self.assertIn("ditemukan pada urutan ke-2", err)
            self.assertIn("tetapi no_urut_kk di Excel adalah 1", err)

            # Case 3: Nama tidak ditemukan sama sekali
            ok, name, err = _find_and_open_matching_art(page, excel_nama="JOKO WIDODO", excel_no_urut="1")
            self.assertFalse(ok)
            self.assertIsNone(name)
            self.assertIn("tidak ditemukan di daftar anggota keluarga", err)

    def test_process_nik_r29_cleaning_rules(self):
        page = MagicMock()
        nik_box = MagicMock()
        inp_nik = MagicMock()

        # Helper to set web_nik
        def set_web_nik(val):
            inp_nik.input_value.return_value = val
            inp_nik.get_attribute.return_value = val

        with patch("modules.cleaning_nik_r29.engine.add_remarks_to_element") as mock_remark, \
             patch("modules.cleaning_nik_r29.engine.safe_fill_input") as mock_fill:

            # Test A: NIK awal di eform beda dengan nik_dtsen di Excel -> Tolak / Dilewati
            set_web_nik("3603010101900001")
            ok, res_nik, err = _process_nik_r29_cleaning(
                page=page,
                nik_box=nik_box,
                inp_nik=inp_nik,
                excel_nik_dtsen="3603010101900002", # BEDA
                excel_nik_length="16",
                excel_matched=""
            )
            self.assertFalse(ok)
            self.assertIn("tidak sama dengan nik_dtsen", err)
            mock_remark.assert_not_called()
            mock_fill.assert_not_called()

            # Test Rule 2: nik_matched kosong dan nik_length = 16 -> NIK tidak diubah, remark #0
            mock_remark.reset_mock()
            mock_fill.reset_mock()
            set_web_nik("3603010101900001")
            ok, res_nik, note = _process_nik_r29_cleaning(
                page=page,
                nik_box=nik_box,
                inp_nik=inp_nik,
                excel_nik_dtsen="3603010101900001",
                excel_nik_length="16",
                excel_matched=""
            )
            self.assertTrue(ok)
            self.assertIn("remark #0", note)
            mock_fill.assert_not_called()
            mock_remark.assert_called_once_with(page, nik_box, "#0", event_bus=None, worker_prefix="")

            # Test Rule 3: nik_matched = 7777 dan nik_length != 16 -> NIK diisi 7777, remark #0
            mock_remark.reset_mock()
            mock_fill.reset_mock()
            set_web_nik("36030111")
            ok, res_nik, note = _process_nik_r29_cleaning(
                page=page,
                nik_box=nik_box,
                inp_nik=inp_nik,
                excel_nik_dtsen="36030111",
                excel_nik_length="8",
                excel_matched="7777"
            )
            self.assertTrue(ok)
            self.assertEqual(res_nik, "7777")
            self.assertIn("remark #0", note)
            mock_fill.assert_called_once_with(page, inp_nik, "7777", event_bus=None)
            mock_remark.assert_called_once_with(page, nik_box, "#0", event_bus=None, worker_prefix="")

            # Test Rule 4: nik_matched = 9999 -> NIK diisi 9999, remark #0
            mock_remark.reset_mock()
            mock_fill.reset_mock()
            set_web_nik("36030122")
            ok, res_nik, note = _process_nik_r29_cleaning(
                page=page,
                nik_box=nik_box,
                inp_nik=inp_nik,
                excel_nik_dtsen="36030122",
                excel_nik_length="8",
                excel_matched="9999"
            )
            self.assertTrue(ok)
            self.assertEqual(res_nik, "9999")
            self.assertIn("remark #0", note)
            mock_fill.assert_called_once_with(page, inp_nik, "9999", event_bus=None)
            mock_remark.assert_called_once_with(page, nik_box, "#0", event_bus=None, worker_prefix="")

            # Test Rule 5: nik_matched 16 digit dan BEDA dengan NIK eform -> ganti NIK nik_matched, remark #3
            mock_remark.reset_mock()
            mock_fill.reset_mock()
            set_web_nik("3603010101900001")
            ok, res_nik, note = _process_nik_r29_cleaning(
                page=page,
                nik_box=nik_box,
                inp_nik=inp_nik,
                excel_nik_dtsen="3603010101900001",
                excel_nik_length="16",
                excel_matched="3603010101900099"
            )
            self.assertTrue(ok)
            self.assertEqual(res_nik, "3603010101900099")
            self.assertIn("remark #3", note)
            mock_fill.assert_called_once_with(page, inp_nik, "3603010101900099", event_bus=None)
            mock_remark.assert_called_once_with(page, nik_box, "#3", event_bus=None, worker_prefix="")

            # Test Rule 5 (safe fallback): nik_matched 16 digit tapi SUDAH SAMA dengan NIK eform -> NIK tetap, remark #3
            mock_remark.reset_mock()
            mock_fill.reset_mock()
            set_web_nik("3603010101900001")
            ok, res_nik, note = _process_nik_r29_cleaning(
                page=page,
                nik_box=nik_box,
                inp_nik=inp_nik,
                excel_nik_dtsen="3603010101900001",
                excel_nik_length="16",
                excel_matched="3603010101900001"
            )
            self.assertTrue(ok)
            self.assertEqual(res_nik, "3603010101900001")
            self.assertIn("remark #3", note)
            mock_fill.assert_not_called()
            mock_remark.assert_called_once_with(page, nik_box, "#3", event_bus=None, worker_prefix="")

            # Test Invalid / Unhandled: nik_matched kosong tapi nik_length != 16
            mock_remark.reset_mock()
            mock_fill.reset_mock()
            set_web_nik("36030111")
            ok, res_nik, err = _process_nik_r29_cleaning(
                page=page,
                nik_box=nik_box,
                inp_nik=inp_nik,
                excel_nik_dtsen="36030111",
                excel_nik_length="8",
                excel_matched=""
            )
            self.assertFalse(ok)
            self.assertIn("nik_matched kosong namun nik_length = 8", err)
            mock_fill.assert_not_called()
            mock_remark.assert_not_called()

if __name__ == "__main__":
    unittest.main()
