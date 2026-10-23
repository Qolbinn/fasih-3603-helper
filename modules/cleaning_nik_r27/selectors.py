# ==============================================================================
# SELECTOR & KONFIGURASI ELEMEN FASIH - DATA CLEANING NIK R27 SE2026
# ==============================================================================

EXCEL_NIK_R27_COLUMNS_CONFIG = {
    # Kolom Identitas & Penugasan dari Excel
    "url": [
        "url", "link_fasih_sm", "link",
        "link fasih", "link_fasih", "tautan"
    ],
    "total_nik": [
        "total_nik", "total nik", "total", "jml_nik", "jumlah_nik"
    ],

    # Kolom Status & Keterangan Eksekusi
    "status": ["status_eksekusi", "status_proses", "status"],
    "keterangan": ["keterangan", "ket", "catatan_eksekusi", "catatan"]
}

# ==============================================================================
# SELECTOR ELEMEN FORMULIR FASIH (CLEANING NIK R27)
# ==============================================================================

NIK_R27_SELECTORS = {
    # Navigasi & Sidebar Blok I (Keterangan Umum Keluarga)
    "sidebar_blok_i": (
        "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='SE2026 - L BLOK I' or contains(@title, 'BLOK I') or contains(text(), 'BLOK I')] | "
        "//*[@title='SE2026 - L BLOK I' or contains(@title, 'BLOK I') or contains(text(), 'BLOK I')]"
    ),
    "sidebar_ket_art": (
        "xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[@title='Keterangan Anggota Keluarga' or contains(text(), 'Keterangan Anggota Keluarga')]"
    ),
    "sidebar_sub_art_items": (
        "xpath=//div[@title='Keterangan Anggota Keluarga']/following-sibling::div[@data-expanded]//div[contains(@class, 'fasih-form-sidebar')]/div[contains(@class, 'cursor-pointer') and @title] | "
        "//div[@title='Keterangan Anggota Keluarga']/following-sibling::div//div[contains(@class, 'fasih-form-sidebar')]/div[contains(@class, 'cursor-pointer') and @title]"
    ),

    # Navigasi Blok Catatan
    "sidebar_blok_catatan": (
        "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='CATATAN' or normalize-space(text())='CATATAN' or contains(text(), 'CATATAN')] | "
        "//*[@title='CATATAN' or normalize-space(text())='CATATAN']"
    ),

    # Rincian 7. NIK (DTSEN) pada Formulir ART
    "container_nik": "div[id^='nik_dtsen#'], div[id*='nik_dtsen']",
    "input_nik": "input[type='text'], input",

    # Tombol Aksi Formulir & Dialog Submit
    "btn_kirim": "button#btn-kirim, button:has-text('Kirim')",
    "btn_konfirmasi_kirim": "div:has-text('Konfirmasi Kirim') button:has-text('Konfirmasi'), div:has-text('Apakah Anda yakin') button:has-text('Konfirmasi'), button:has-text('Konfirmasi')",
    "dialog_sukses": "div[role='alertdialog']:has-text('Assignment Berhasil Disubmit'), h2:has-text('Assignment Berhasil Disubmit'), p:has-text('Perubahan Anda berhasil disimpan'), div[role='dialog']:has-text('Berhasil')"
}
