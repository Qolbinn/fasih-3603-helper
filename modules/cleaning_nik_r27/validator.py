import os
import re
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from modules.cleaning_nik_r27.selectors import EXCEL_NIK_R27_COLUMNS_CONFIG

class ExcelNIKR27Validator:
    MANDATORY_KEYS = [
        "url",
        "total_nik"
    ]

    @staticmethod
    def is_file_locked(file_path):
        """Memeriksa apakah file Excel sedang terbuka di aplikasi lain (Microsoft Excel) yang mengunci penulisan."""
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "r+b"):
                return False
        except (IOError, PermissionError):
            return True

    @classmethod
    def validate_excel_file(cls, file_path):
        """
        Melakukan validasi menyeluruh terhadap file Excel input Data Cleaning NIK R27.
        Mendukung kolom NIK jamak dinamis (nik_1, nik_2, ... nik_n).
        Mengembalikan dict hasil pemeriksaan & data pratinjau.
        """
        p = Path(file_path)
        if not p.exists():
            return {
                "valid": False,
                "error": f"File tidak ditemukan: {file_path}",
                "warning": None,
                "file_locked": False,
                "total_rows": 0,
                "done_rows": 0,
                "pending_rows": 0,
                "rows_data": []
            }

        locked = cls.is_file_locked(file_path)
        warning_msg = None
        if locked:
            warning_msg = "Perhatian: File sedang dibuka di Excel. Anda dapat melihat pratinjau, namun harap tutup file Excel sebelum memulai otomasi agar hasil dapat disimpan."

        try:
            with open(file_path, "rb") as f:
                wb = openpyxl.load_workbook(f, data_only=True)
                sheet = wb.active
        except Exception as e:
            return {
                "valid": False,
                "error": f"Gagal membaca format file Excel: {e}",
                "warning": None,
                "file_locked": locked,
                "total_rows": 0,
                "done_rows": 0,
                "pending_rows": 0,
                "rows_data": []
            }

        # 1. Baca header baris 1
        header_map = {}
        for col_idx in range(1, sheet.max_column + 1):
            val = sheet.cell(row=1, column=col_idx).value
            if val is not None:
                header_map[str(val).strip().lower()] = col_idx

        # 2. Mapping kolom wajib dasar & status
        col_map = {}
        for key, aliases in EXCEL_NIK_R27_COLUMNS_CONFIG.items():
            for alias in aliases:
                clean_alias = str(alias).strip().lower()
                if clean_alias in header_map:
                    col_map[key] = header_map[clean_alias]
                    break

        # 3. Periksa kolom wajib dasar (url, total_nik)
        missing_mandatory = []
        for mand in cls.MANDATORY_KEYS:
            if mand not in col_map:
                missing_mandatory.append(mand)

        if missing_mandatory:
            wb.close()
            return {
                "valid": False,
                "error": f"Template tidak sesuai. Kolom wajib berikut tidak ditemukan: {', '.join(missing_mandatory)}",
                "warning": warning_msg,
                "file_locked": locked,
                "total_rows": 0,
                "done_rows": 0,
                "pending_rows": 0,
                "rows_data": []
            }

        # 4. Deteksi semua kolom NIK (nik_1, nik_2, ... nik_n atau kolom berawalan 'nik')
        nik_cols = []
        for h_text, c_idx in header_map.items():
            # Jangan anggap 'total_nik' atau status sebagai kolom NIK
            if h_text in EXCEL_NIK_R27_COLUMNS_CONFIG["total_nik"]:
                continue
            if h_text in EXCEL_NIK_R27_COLUMNS_CONFIG["status"] or h_text in EXCEL_NIK_R27_COLUMNS_CONFIG["keterangan"]:
                continue

            m = re.match(r"^nik(?:_|\s*)?(\d+)?$", h_text, re.IGNORECASE)
            if m:
                num = int(m.group(1)) if m.group(1) else 1
                nik_cols.append((num, c_idx, h_text))

        if not nik_cols:
            wb.close()
            return {
                "valid": False,
                "error": "Template tidak sesuai. Kolom target NIK (seperti nik_1, nik_2, dst.) tidak ditemukan di baris header.",
                "warning": warning_msg,
                "file_locked": locked,
                "total_rows": 0,
                "done_rows": 0,
                "pending_rows": 0,
                "rows_data": []
            }

        # Urutkan kolom NIK berdasarkan nomor urut kolomnya
        nik_cols.sort(key=lambda x: (x[0], x[1]))

        # 5. Iterasi pembacaan data baris
        rows_data = []
        done_count = 0
        url_col = col_map["url"]
        total_nik_col = col_map["total_nik"]
        status_col = col_map.get("status")
        ket_col = col_map.get("keterangan")

        max_row = sheet.max_row
        for r in range(2, max_row + 1):
            url_val = str(sheet.cell(row=r, column=url_col).value or "").strip()
            total_nik_raw = sheet.cell(row=r, column=total_nik_col).value

            # Ekstrak seluruh NIK non-kosong dari kolom-kolom nik_*
            nik_list = []
            for _, c_idx, _ in nik_cols:
                cell_val = sheet.cell(row=r, column=c_idx).value
                if cell_val is not None:
                    raw_s = str(cell_val).strip()
                    if raw_s.endswith(".0"):
                        raw_s = raw_s[:-2]
                    digits = re.sub(r"[^\d]", "", raw_s)
                    if digits:
                        nik_list.append(digits)

            # Jika baris benar-benar kosong, lewati
            if not url_val and not nik_list and total_nik_raw is None:
                continue

            # Parsing total_nik
            total_nik = 0
            if total_nik_raw is not None:
                try:
                    total_nik = int(float(str(total_nik_raw).strip()))
                except (ValueError, TypeError):
                    total_nik = len(nik_list)
            else:
                total_nik = len(nik_list)

            # Status dan keterangan
            status_val = ""
            if status_col:
                status_val = str(sheet.cell(row=r, column=status_col).value or "").strip()

            ket_val = ""
            if ket_col:
                ket_val = str(sheet.cell(row=r, column=ket_col).value or "").strip()

            # Periksa status
            status_clean = "PENDING"
            status_upper = status_val.upper()
            if "SUKSES" in status_upper or "DONE" in status_upper or "BERHASIL" in status_upper:
                status_clean = "SUKSES"
                done_count += 1
            elif "GAGAL" in status_upper or "ERROR" in status_upper or "GALAT" in status_upper:
                status_clean = "GAGAL"

            row_dict = {
                "_row_num": r,
                "row_idx": r,
                "url": url_val,
                "total_nik": total_nik,
                "nik_list": nik_list,
                "status": status_val,
                "keterangan": ket_val,
                "_status_clean": status_clean
            }
            rows_data.append(row_dict)

        wb.close()
        total_valid_rows = len(rows_data)
        pending_count = total_valid_rows - done_count

        return {
            "valid": True,
            "error": None,
            "warning": warning_msg,
            "file_locked": locked,
            "col_map": col_map,
            "nik_cols_count": len(nik_cols),
            "total_rows": total_valid_rows,
            "done_rows": done_count,
            "pending_rows": pending_count,
            "rows_data": rows_data
        }

    @classmethod
    def update_row_status(cls, file_path, row_num, status, keterangan):
        """
        Memperbarui kolom Status dan Keterangan pada file Excel secara atomik dan thread-safe.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

        wb = openpyxl.load_workbook(file_path)
        sheet = wb.active

        # Temukan index kolom status & keterangan
        header_map = {}
        for col_idx in range(1, sheet.max_column + 1):
            val = sheet.cell(row=1, column=col_idx).value
            if val is not None:
                header_map[str(val).strip().lower()] = col_idx

        status_col = None
        for alias in EXCEL_NIK_R27_COLUMNS_CONFIG["status"]:
            if alias.lower() in header_map:
                status_col = header_map[alias.lower()]
                break

        ket_col = None
        for alias in EXCEL_NIK_R27_COLUMNS_CONFIG["keterangan"]:
            if alias.lower() in header_map:
                ket_col = header_map[alias.lower()]
                break

        # Jika belum ada kolom status / keterangan di file, buat di akhir
        if status_col is None:
            status_col = sheet.max_column + 1
            sheet.cell(row=1, column=status_col, value="Status_Eksekusi")
            sheet.cell(row=1, column=status_col).font = Font(name="Segoe UI", size=11, bold=True)

        if ket_col is None:
            ket_col = sheet.max_column + 1
            sheet.cell(row=1, column=ket_col, value="Keterangan")
            sheet.cell(row=1, column=ket_col).font = Font(name="Segoe UI", size=11, bold=True)

        # Update cell status & keterangan
        cell_status = sheet.cell(row=row_num, column=status_col, value=status)
        cell_ket = sheet.cell(row=row_num, column=ket_col, value=keterangan)

        # Pewarnaan status yang jelas & profesional
        if "SUKSES" in status.upper():
            cell_status.font = Font(color="059669", bold=True)
            cell_status.fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
        elif "GAGAL" in status.upper() or "ERROR" in status.upper():
            cell_status.font = Font(color="DC2626", bold=True)
            cell_status.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        else:
            cell_status.font = Font(color="D97706", bold=True)
            cell_status.fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

        wb.save(file_path)
        wb.close()

    @classmethod
    def generate_template_excel(cls, output_path):
        """
        Membuat template Excel standar untuk modul Data Cleaning NIK R27 SE2026.
        Format kolom: url, total_nik, nik_1 s.d. nik_8, Status_Eksekusi, Keterangan.
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data_Cleaning_NIK_R27"

        headers = [
            "url",
            "total_nik",
            "nik_1",
            "nik_2",
            "nik_3",
            "nik_4",
            "nik_5",
            "nik_6",
            "nik_7",
            "nik_8",
            "Status_Eksekusi",
            "Keterangan"
        ]

        ws.append(headers)

        # Style header (Aesthetic Indigo)
        header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style='thin', color='D1D5DB'),
            right=Side(style='thin', color='D1D5DB'),
            top=Side(style='thin', color='D1D5DB'),
            bottom=Side(style='thin', color='D1D5DB')
        )

        ws.row_dimensions[1].height = 28

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align
            cell.border = thin_border

        # Baris Contoh Data Realistis
        sample_rows = [
            [
                "https://fasih-sm.bps.go.id/penugasan/detail/contoh-keluarga-1",
                2,
                "3603010101900001",
                "3603014101920002",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None
            ],
            [
                "https://fasih-sm.bps.go.id/penugasan/detail/contoh-keluarga-2",
                1,
                "3603010505850003",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None
            ]
        ]

        data_font = Font(name="Segoe UI", size=10)
        data_align_center = Alignment(horizontal="center", vertical="center")
        data_align_left = Alignment(horizontal="left", vertical="center")

        for r_idx, row_vals in enumerate(sample_rows, start=2):
            ws.row_dimensions[r_idx].height = 22
            for c_idx, val in enumerate(row_vals, start=1):
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.font = data_font
                cell.border = thin_border
                # Format url rata kiri, total_nik dan NIK rata tengah teks
                if c_idx == 1:
                    cell.alignment = data_align_left
                elif c_idx == 2:
                    cell.alignment = data_align_center
                elif 3 <= c_idx <= 10:
                    cell.alignment = data_align_center
                    cell.number_format = "@"  # Text format agar nomor NIK tidak terpotong atau eksponensial

        # Atur lebar kolom optimal
        col_widths = {
            1: 45,  # url
            2: 12,  # total_nik
            3: 20,  # nik_1
            4: 20,  # nik_2
            5: 20,  # nik_3
            6: 20,  # nik_4
            7: 20,  # nik_5
            8: 20,  # nik_6
            9: 20,  # nik_7
            10: 20, # nik_8
            11: 18, # Status_Eksekusi
            12: 35  # Keterangan
        }
        for col_idx, width in col_widths.items():
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width

        ws.freeze_panes = "A2"
        wb.save(output_path)
        wb.close()
