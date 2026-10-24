import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.kbli_pmm.selectors import KBLI_PMM_SELECTORS, EXCEL_KBLI_PMM_COLUMNS_CONFIG
from modules.kbli_pmm.validator import ExcelKBLIPMMValidator
from modules.kbli_pmm.engine import _process_pmm_characteristics, KBLIPMMEngine
from modules.kbli_pmm.view import KBLIPMMView

print("1. Testing KBLI PMM selectors...")
assert "container_produk_sendiri" in KBLI_PMM_SELECTORS
assert "container_layanan_mamin" in KBLI_PMM_SELECTORS
assert "container_lokasi_usaha" in KBLI_PMM_SELECTORS
assert "kbli_akhir" in EXCEL_KBLI_PMM_COLUMNS_CONFIG
print("   Selectors OK!")

print("2. Testing _process_pmm_characteristics validation...")
# Invalid KBLI should return False, "DILEWATI", ... without touching page
ok, st, ket = _process_pmm_characteristics(None, kbli_akhir="47112")
assert ok is False
assert st == "DILEWATI"
assert "bukan target PMM" in ket
print(f"   Non-target KBLI handled correctly: {ket}")

ok_empty, st_empty, ket_empty = _process_pmm_characteristics(None, kbli_akhir="")
assert ok_empty is False
assert st_empty == "DILEWATI"
print(f"   Empty KBLI handled correctly: {ket_empty}")

print("3. Testing template generator and validator...")
test_tpl = "scratch/test_pmm_template.xlsx"
ExcelKBLIPMMValidator.generate_template(test_tpl)
assert os.path.exists(test_tpl), "Template file was not created"

val_res = ExcelKBLIPMMValidator.validate_excel_file(test_tpl)
assert val_res["valid"] is True, f"Validation failed: {val_res.get('error')}"
assert val_res["total_rows"] == 2, f"Expected 2 sample rows, got {val_res['total_rows']}"
print(f"   Template validated successfully! Rows: {val_res['total_rows']}, Pending: {val_res['pending_rows']}")

print("\nALL PMM LOGIC CHECKS PASSED SUCCESSFULLY!")
