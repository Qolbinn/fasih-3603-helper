# ==============================================================================
# SELECTOR & CONFIGURASI ELEMEN FASIH - DC USAHA #3603
# ==============================================================================

EXCEL_COLUMNS_CONFIG = {
    # Kolom Identitas & URL (Hanya URL yang wajib, nama usaha untuk pencarian sub-sidebar)
    "url": ["link fasih sm", "link_fasih_sm", "url", "link", "link fasih", "link_fasih", "tautan", "tautan fasih"],
    "nama_usaha": ["nama usaha", "nama_usaha", "nama perusahaan", "kegiatan_utama", "keg_utama"],
    "id": ["assignment_id", "id", "no", "id penugasan"],

    # Kolom status & log
    "status": ["status_eksekusi", "status", "status_proses"],
    "keterangan": ["keterangan", "ket", "catatan_eksekusi", "catatan"]
}

# Selector Container Total (Tahunan)
TOTAL_PENGELUARAN_SELECTOR = "div[id^='total_pengeluaran#'], div[id='total_pengeluaran']"
TOTAL_PENDAPATAN_SELECTOR = "div[id^='total_pendapatan#'], div[id='total_pendapatan']"

# Selector Container Total (Bulanan - Khusus Usaha Baru Buka / Berjalan Tahun 2026)
TOTAL_PENGELUARAN_BLN_SELECTOR = "div[id^='total_pengeluaran_bln#'], div[id='total_pengeluaran_bln']"
TOTAL_PENDAPATAN_BLN_SELECTOR = "div[id^='total_pendapatan_bln#'], div[id='total_pendapatan_bln']"

# Selector Blok Sidebar & Menu
BLOK_II_XPATH = "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')] | //*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')]"
BLOK_CATATAN_XPATH = "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='CATATAN' or normalize-space(text())='CATATAN' or contains(text(), 'CATATAN')] | //*[@title='CATATAN' or normalize-space(text())='CATATAN']"

# Selector Tombol Submit & Dialog Konfirmasi
KIRIM_BUTTON_XPATH = "button#btn-kirim, button:has-text('Kirim')"
CONFIRM_BUTTON_XPATH = "button:has-text('Konfirmasi'), button:has-text('Kirim')"
RINGKASAN_KIRIM_SELECTOR = "div[role='dialog'] button:has-text('Kirim'), div[role='alertdialog'] button:has-text('Kirim'), div:has(button:has-text('Batal')) button:has-text('Kirim')"
KONFIRMASI_KIRIM_BUTTON_SELECTOR = "div:has-text('Konfirmasi Kirim') button:has-text('Konfirmasi'), div:has-text('Apakah Anda yakin') button:has-text('Konfirmasi'), button:has-text('Konfirmasi')"
SUCCESS_SUBMIT_DIALOG_SELECTOR = "div[role='alertdialog']:has-text('Assignment Berhasil Disubmit'), h2:has-text('Assignment Berhasil Disubmit'), p:has-text('Perubahan Anda berhasil disimpan')"
