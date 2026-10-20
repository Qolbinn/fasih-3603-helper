import os
import csv
import threading
from datetime import datetime
from pathlib import Path
from config import AUDIT_DIR

class AuditLogger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AuditLogger, cls).__new__(cls)
                cls._instance._init_audit()
            return cls._instance

    def _init_audit(self):
        self._file_lock = threading.Lock()
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.audit_file = AUDIT_DIR / f"audit_log_{today_str}.csv"
        self._ensure_header()

    def _ensure_header(self):
        with self._file_lock:
            if not self.audit_file.exists():
                headers = [
                    "timestamp",
                    "row_index",
                    "assignment_id",
                    "nama_usaha",
                    "status",
                    "remarks_pengeluaran",
                    "pengeluaran_clean",
                    "pengeluaran_raw",
                    "remarks_pendapatan",
                    "pendapatan_clean",
                    "pendapatan_raw",
                    "remarks_aset",
                    "aset_clean",
                    "aset_raw",
                    "aset_tanah_baru",
                    "aset_non_tanah_baru",
                    "galat_count",
                    "keterangan",
                    "user_sso",
                    "link_fasih"
                ]
                with open(self.audit_file, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)

    def record_row(self, data_dict):
        """Mencatat satu baris eksekusi audit ke file CSV secara aman."""
        with self._file_lock:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                data_dict.get("row_index", ""),
                data_dict.get("assignment_id", ""),
                data_dict.get("nama_usaha", ""),
                data_dict.get("status", ""),
                data_dict.get("remarks_pengeluaran", ""),
                data_dict.get("pengeluaran_clean", ""),
                data_dict.get("pengeluaran_raw", ""),
                data_dict.get("remarks_pendapatan", ""),
                data_dict.get("pendapatan_clean", ""),
                data_dict.get("pendapatan_raw", ""),
                data_dict.get("remarks_aset", ""),
                data_dict.get("aset_clean", ""),
                data_dict.get("aset_raw", ""),
                data_dict.get("aset_tanah_baru", ""),
                data_dict.get("aset_non_tanah_baru", ""),
                data_dict.get("galat_count", 0),
                data_dict.get("keterangan", ""),
                data_dict.get("user_sso", ""),
                data_dict.get("link_fasih", "")
            ]
            try:
                with open(self.audit_file, "a", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(row)
            except Exception:
                pass

audit_logger = AuditLogger()
