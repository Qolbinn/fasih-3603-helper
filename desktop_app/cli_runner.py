import os
import sys

# ==============================================================================
# COMPATIBILITY GUARD: NumPy 2.x & openpyxl Compatibility Guard
# ==============================================================================
if getattr(sys, "frozen", False):
    for _mod in ("numpy", "scipy", "pandas", "matplotlib"):
        sys.modules[_mod] = None
else:
    try:
        import numpy as _np
        if _np is not None:
            _type_map = {
                'short': getattr(_np, 'int16', int),
                'ushort': getattr(_np, 'uint16', int),
                'intc': getattr(_np, 'int32', int),
                'uintc': getattr(_np, 'uint32', int),
                'int_': getattr(_np, 'int64', int),
                'uint': getattr(_np, 'uint64', int),
                'longlong': getattr(_np, 'int64', int),
                'ulonglong': getattr(_np, 'uint64', int),
                'half': getattr(_np, 'float16', float),
                'float16': float,
                'single': getattr(_np, 'float32', float),
                'double': getattr(_np, 'float64', float),
                'longdouble': getattr(_np, 'float64', float),
                'int8': getattr(_np, 'int8', int),
                'int16': getattr(_np, 'int16', int),
                'int32': getattr(_np, 'int32', int),
                'int64': getattr(_np, 'int64', int),
                'uint8': getattr(_np, 'uint8', int),
                'uint16': getattr(_np, 'uint16', int),
                'uint32': getattr(_np, 'uint32', int),
                'uint64': getattr(_np, 'uint64', int),
                'intp': getattr(_np, 'int64', int),
                'uintp': getattr(_np, 'uint64', int),
                'float32': float,
                'float64': float,
                'bool_': bool,
                'floating': float,
                'integer': int,
            }
            for _k, _v in _type_map.items():
                if not hasattr(_np, _k):
                    setattr(_np, _k, _v)
    except (ImportError, Exception):
        pass

import argparse
from pathlib import Path

# Tambahkan direktori aplikasi ke sys.path
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core.logger import logger
from core.event_bus import EventBus
from core.browser_manager import BrowserManager
from modules.cleaning_usaha.validator import ExcelValidator
from modules.cleaning_usaha.engine import DataCleaningEngine

def main():
    parser = argparse.ArgumentParser(description="FASIH 3603 Helper - CLI Runner untuk Debugging & Uji Paritas")
    parser.add_argument("--file", "-f", default=None, help="Path ke file Excel flag_clean.xlsx")
    parser.add_argument("--auto", action="store_true", help="Mode Produksi: Langsung submit otomatis tanpa tahan konfirmasi")
    parser.add_argument("--template", action="store_true", help="Buat file template_flag_clean.xlsx dan keluar")
    parser.add_argument("--no-minimize", action="store_true", help="Jangan meminimalkan browser saat berjalan")
    parser.add_argument("--start", type=int, default=2, help="Baris awal (default: 2)")
    parser.add_argument("--end", type=int, default=None, help="Baris akhir")
    args = parser.parse_args()

    print("========================================================")
    print("      FASIH 3603 Helper - Standalone CLI Runner         ")
    print("========================================================")

    if args.template:
        out_path = Path("template_flag_clean.xlsx").resolve()
        ExcelValidator.generate_template(str(out_path))
        logger.success(f"Template berhasil dibuat di: {out_path}")
        return

    # 1. Tentukan path file Excel
    excel_path = args.file
    if not excel_path:
        default_candidate = APP_DIR.parent / "Data Cleaning" / "data" / "flag_clean.xlsx"
        if default_candidate.exists():
            excel_path = str(default_candidate)
        else:
            excel_path = input(">> Masukkan path file Excel: ").strip().strip('"')

    if not os.path.exists(excel_path):
        logger.error(f"File Excel tidak ditemukan: {excel_path}")
        return

    # 2. Validasi template
    logger.info("Memvalidasi template Excel...")
    val_res = ExcelValidator.validate_excel_file(excel_path)
    if not val_res["valid"]:
        logger.error(f"Validasi Gagal: {val_res['error']}")
        return

    logger.success(f"Template Valid! Total: {val_res['total_rows']} baris | Belum: {val_res['pending_rows']} | Selesai: {val_res['done_rows']}")

    # 3. Cek browser
    is_running, b_name = BrowserManager.is_cdp_running()
    if not is_running:
        logger.warning("Browser belum aktif di port 9222. Mencoba meluncurkan browser...")
        launched, msg = BrowserManager.launch_browser()
        if not launched:
            logger.error(f"Gagal meluncurkan browser: {msg}")
            return
        input(">> Silakan login SSO di Chrome, lalu tekan ENTER di sini untuk lanjut... ")

    # 4. Jalankan Engine
    import threading
    import time
    event_bus = EventBus()
    config_opts = {
        "debug_review_submit": not args.auto,
        "auto_minimize": not args.no_minimize,
        "row_start": args.start,
        "row_end": args.end
    }

    def cli_event_listener():
        while True:
            events = event_bus.poll_events()
            for ev_type, payload in events:
                if ev_type == "waiting_confirm_submit":
                    try:
                        input(f"\n>> [REVIEW SUBMIT] Baris {payload['row_idx']} [{payload['nama_usaha']}]: Silakan periksa di Chrome, lalu tekan [ENTER] untuk submit formulir & lanjut: ")
                    except Exception:
                        pass
                    event_bus.confirm_submit()
                elif ev_type == "all_completed":
                    return
            time.sleep(0.2)

    t = threading.Thread(target=cli_event_listener, daemon=True)
    t.start()

    engine = DataCleaningEngine(excel_path, event_bus, config_opts)
    engine.run()

if __name__ == "__main__":
    main()
