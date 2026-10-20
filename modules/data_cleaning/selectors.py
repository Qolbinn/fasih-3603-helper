# ==============================================================================
# SELECTOR & CONFIGURASI ELEMEN FASIH - DATA CLEANING SE2026
# (Semua selector terpusat di sini untuk memudahkan pemeliharaan di masa depan)
# ==============================================================================

EXCEL_COLUMNS_CONFIG = {
    # Kolom Identitas & URL
    "url": ["link_fasih_sm", "url", "link", "link fasih", "link_fasih"],
    "nama_usaha": ["nama usaha", "nama_usaha", "nama perusahaan"],
    "id": ["assignment_id", "id", "no", "id penugasan"],

    # Kolom Pembanding Total
    "total_pengeluaran": ["total pengeluaran"],
    "total_pengeluaran_raw": ["total pengeluaran [raw]", "total pengeluaran raw", "total pengeluaran_raw"],

    "total_pendapatan": ["total pendapatan"],
    "total_pendapatan_raw": ["total pendapatan [raw]", "total pendapatan raw", "total pendapatan_raw"],

    "total_aset": ["total aset", "total asset"],
    "total_aset_raw": ["total aset [raw]", "total aset raw", "total asset [raw]", "total asset raw"],

    # Komponen Pengeluaran
    "upah dan gaji": ["upah dan gaji", "upah & gaji", "total upah dan gaji", "gaji"],
    "biaya produksi": ["biaya produksi", "produksi"],
    "biaya pembelian barang yang terjual": ["biaya pembelian barang yang terjual", "biaya pembelian", "pembelian barang terjual"],
    "biaya operasional": ["biaya operasional", "operasional"],
    "biaya non operasional": ["biaya non operasional", "biaya non-operasional", "non operasional"],

    # Komponen Pendapatan
    "nilai pendapatan barang dan jasa": ["nilai pendapatan barang dan jasa", "pendapatan barang dan jasa", "penjualan barang dan jasa"],
    "pendapatan lainnya": ["pendapatan lainnya", "pendapatan lain"],

    # Status & Log
    "status": ["status_eksekusi", "status"],
    "keterangan": ["keterangan", "ket"]
}

# Mapping komponen pengeluaran (Catatan: '_bln' di-comment sementara)
PENGELUARAN_MAP = [
    {
        "name": "Upah dan Gaji",
        "excel_key": "upah dan gaji",
        # "selector_bln": "div[id^='gaji_bln#']",
        "selector": "div[id^='gaji#']",
        "fallback": "xpath=//div[contains(., 'Total upah dan gaji') and .//input[@type='text']]"
    },
    {
        "name": "Biaya Produksi",
        "excel_key": "biaya produksi",
        # "selector_bln": "div[id^='biaya_produksi_bln#']",
        "selector": "div[id^='biaya_produksi#']",
        "fallback": "xpath=//div[contains(., 'Biaya produksi') and .//input[@type='text']]"
    },
    {
        "name": "Biaya Pembelian Barang yang Terjual",
        "excel_key": "biaya pembelian barang yang terjual",
        # "selector_bln": "div[id^='biaya_pembelian_bln#']",
        "selector": "div[id^='biaya_pembelian#']",
        "fallback": "xpath=//div[contains(., 'Biaya pembelian barang yang terjual') and .//input[@type='text']]"
    },
    {
        "name": "Biaya Operasional",
        "excel_key": "biaya operasional",
        # "selector_bln": "div[id^='operasional_bln#']",
        "selector": "div[id^='operasional#']",
        "fallback": "xpath=//div[contains(., 'Biaya operasional') and .//input[@type='text']]"
    },
    {
        "name": "Biaya Non Operasional",
        "excel_key": "biaya non operasional",
        # "selector_bln": "div[id^='non_operasional_bln#']",
        "selector": "div[id^='non_operasional#']",
        "fallback": "xpath=//div[contains(., 'Biaya non-operasional') and .//input[@type='text']]"
    },
]

# Mapping komponen pendapatan (Catatan: '_bln' di-comment sementara)
PENDAPATAN_MAP = [
    {
        "name": "Nilai Pendapatan Barang dan Jasa",
        "excel_key": "nilai pendapatan barang dan jasa",
        # "selector_bln": "div[id^='nilai_pendapatan_bln#']",
        "selector": "div[id^='nilai_pendapatan#']",
        "fallback": "xpath=//div[contains(., 'Nilai penjualan barang dan jasa') and .//input[@type='text']]"
    },
    {
        "name": "Pendapatan Lainnya",
        "excel_key": "pendapatan lainnya",
        # "selector_bln": "div[id^='pendapatan_lain_bln#']",
        "selector": "div[id^='pendapatan_lain#']",
        "fallback": "xpath=//div[contains(., 'Pendapatan lainnya yang dihasilkan') and .//input[@type='text']]"
    },
]

# Mapping komponen Total Aset (Tanah, Selain Tanah, dan Field Total Aset untuk Remarks)
ASET_MAP = {
    "tanah_bangunan": {
        "name": "Aset Tanah dan Bangunan",
        # "selector_bln": "div[id^='aset_tanah_bln#']",
        "selector": "div[id^='aset_usaha_thn#'], div[id^='aset_tanah#']",
        "fallback": "xpath=//div[contains(., 'aset tanah dan bangunan') and .//input[@type='text']]"
    },
    "selain_tanah": {
        "name": "Aset Selain Tanah dan Bangunan",
        # "selector_bln": "div[id^='aset_lain_bln#']",
        "selector": "div[id^='aset_lain_thn#'], div[id^='aset_lain#']",
        "fallback": "xpath=//div[contains(., 'aset selain tanah dan bangunan') and .//input[@type='text']]"
    },
    "total_aset": {
        "name": "Total Aset (Field Remarks)",
        # "selector_bln": "div[id^='total_aset_bln#']",
        "selector": "div[id^='total_aset_thn#'], div[id^='total_aset#']",
        "fallback": "xpath=//div[contains(., 'Nilai total aset') and .//button[contains(@title, 'Catatan')]]"
    }
}

# Selector Container Total
TOTAL_PENGELUARAN_SELECTOR = "div[id^='total_pengeluaran#']"
TOTAL_PENDAPATAN_SELECTOR = "div[id^='total_pendapatan#']"

# Selector Blok Sidebar & Menu
BLOK_II_XPATH = "xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[@title='SE2026 - L BLOK II' or contains(text(), 'BLOK II')]"
BLOK_CATATAN_XPATH = "xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[@title='CATATAN' or normalize-space(text())='CATATAN']"

# Selector Tombol Submit & Dialog Konfirmasi
KIRIM_BUTTON_XPATH = "button#btn-kirim, button:has-text('Kirim')"
CONFIRM_BUTTON_XPATH = "button:has-text('Konfirmasi'), button:has-text('Kirim')"
RINGKASAN_KIRIM_SELECTOR = "div:has(button:has-text('Batal')) button:has-text('Kirim')"
KONFIRMASI_KIRIM_BUTTON_SELECTOR = "div:has-text('Konfirmasi Kirim') button:has-text('Konfirmasi'), div:has-text('Apakah Anda yakin') button:has-text('Konfirmasi'), button:has-text('Konfirmasi')"
SUCCESS_SUBMIT_DIALOG_SELECTOR = "div[role='alertdialog']:has-text('Assignment Berhasil Disubmit'), h2:has-text('Assignment Berhasil Disubmit'), p:has-text('Perubahan Anda berhasil disimpan')"
