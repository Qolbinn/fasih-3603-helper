import os
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from modules.kbli_pmm.selectors import EXCEL_KBLI_PMM_COLUMNS_CONFIG

class ExcelKBLIPMMValidator:
    MANDATORY_KEYS = [
        "keg_utama",
        "kbli_akhir",
        "url",
        "status_kbli",
        "kbli_terbaru"
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
        Melakukan validasi menyeluruh terhadap file Excel input KBLI PMM.
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

        # 2. Mapping konfigurasi ke index kolom sebenarnya
        col_map = {}
        for key, aliases in EXCEL_KBLI_PMM_COLUMNS_CONFIG.items():
            for alias in aliases:
                clean_alias = str(alias).strip().lower()
                if clean_alias in header_map:
                    col_map[key] = header_map[clean_alias]
                    break

        # 3. Periksa kolom wajib
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

        # 4. Baca baris data & hitung statistik
        rows_data = []
        total_rows = 0
        done_rows = 0
        pending_rows = 0

        max_r = sheet.max_row
        for r in range(2, max_r + 1):
            url_val = sheet.cell(row=r, column=col_map["url"]).value
            if url_val is None or not str(url_val).strip():
                continue

            total_rows += 1
            keg_utama = str(sheet.cell(row=r, column=col_map["keg_utama"]).value or "").strip()
            kbli_akhir = str(sheet.cell(row=r, column=col_map["kbli_akhir"]).value or "").strip()
            url = str(url_val).strip()

            status_kbli_val = sheet.cell(row=r, column=col_map["status_kbli"]).value
            status_kbli = str(status_kbli_val or "").strip()

            kbli_terbaru_val = sheet.cell(row=r, column=col_map["kbli_terbaru"]).value
            kbli_terbaru = str(kbli_terbaru_val or "").strip()

            status_val = ""
            if "status" in col_map:
                status_val = str(sheet.cell(row=r, column=col_map["status"]).value or "").strip()

            keterangan_val = ""
            if "keterangan" in col_map:
                keterangan_val = str(sheet.cell(row=r, column=col_map["keterangan"]).value or "").strip()

            is_done = (status_val.lower() == "berhasil") or (status_val != "" and "berhasil" in status_val.lower())
            if is_done:
                done_rows += 1
            else:
                pending_rows += 1

            rows_data.append({
                "row_idx": r,
                "keg_utama": keg_utama,
                "kbli_akhir": kbli_akhir,
                "url": url,
                "status_kbli": status_kbli,
                "kbli_terbaru": kbli_terbaru,
                "status": status_val,
                "keterangan": keterangan_val,
                "is_done": is_done
            })

        wb.close()

        if total_rows == 0:
            return {
                "valid": False,
                "error": "File Excel valid, tetapi tidak ada baris data penugasan (kolom URL kosong).",
                "warning": warning_msg,
                "file_locked": locked,
                "total_rows": 0,
                "done_rows": 0,
                "pending_rows": 0,
                "rows_data": []
            }

        return {
            "valid": True,
            "error": None,
            "warning": warning_msg,
            "file_locked": locked,
            "total_rows": total_rows,
            "done_rows": done_rows,
            "pending_rows": pending_rows,
            "rows_data": rows_data,
            "col_map": col_map
        }

    @classmethod
    def generate_template(cls, target_path):
        """Membuat file template Excel standar untuk KBLI PMM."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data_KBLI_PMM"

        headers = [
            ("keg_utama", "Kegiatan Utama"),
            ("kbli_akhir", "KBLI Akhir"),
            ("url", "Link Penugasan Fasih (URL)"),
            ("Status_KBLI", "Status KBLI"),
            ("KBLI_Terbaru", "KBLI Terbaru"),
            ("Status_Eksekusi", "Status Eksekusi (Opsional)"),
            ("Keterangan", "Keterangan (Opsional)")
        ]

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="E11D48", end_color="E11D48", fill_type="solid") # Rose KBLI PMM theme
        header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

        thin_border = Border(
            left=Side(style="thin", color="CCCCCC"),
            right=Side(style="thin", color="CCCCCC"),
            top=Side(style="thin", color="CCCCCC"),
            bottom=Side(style="thin", color="CCCCCC")
        )

        ws.row_dimensions[1].height = 28

        for col_idx, (col_id, col_label) in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_id)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

        # Contoh baris data sampel PMM (Status_KBLI: "Tetap" atau "Ganti", KBLI_Terbaru terisi jika "Ganti")
        sample_rows = [
            (
                "Restoran dan Rumah Makan",
                "56101",
                "https://fasih-sm.bps.go.id/assignment/detail/sample-pmm-1",
                "Tetap",
                "",
                "",
                ""
            ),
            (
                "Kedai Makanan dan Minuman Tenda",
                "56102",
                "https://fasih-sm.bps.go.id/assignment/detail/sample-pmm-2",
                "Ganti",
                "56101",
                "",
                ""
            )
        ]

        data_font = Font(name="Calibri", size=10)
        data_align = Alignment(vertical="center")

        for r_idx, row_values in enumerate(sample_rows, 2):
            ws.row_dimensions[r_idx].height = 22
            for c_idx, val in enumerate(row_values, 1):
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.font = data_font
                cell.alignment = data_align
                cell.border = thin_border

        # Atur lebar kolom otomatis
        col_widths = {
            1: 45, # keg_utama
            2: 14, # kbli_akhir
            3: 45, # url
            4: 16, # Status_KBLI
            5: 16, # KBLI_Terbaru
            6: 18, # Status_Eksekusi
            7: 25  # Keterangan
        }
        for col_idx, width in col_widths.items():
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = width

        # Data validation dropdown untuk kolom Status_KBLI (D2:D1000)
        dv = DataValidation(type="list", formula1='"Tetap,Ganti"', allow_blank=True)
        dv.error = 'Status_KBLI hanya boleh diisi "Tetap" atau "Ganti"'
        dv.errorTitle = 'Nilai Tidak Valid'
        dv.prompt = 'Pilih "Tetap" atau "Ganti"'
        dv.promptTitle = 'Status KBLI'
        ws.add_data_validation(dv)
        dv.add("D2:D1000")

        ws.freeze_panes = "A2"
        wb.save(target_path)
        wb.close()
