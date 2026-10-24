# ==============================================================================
# SELECTOR & KONFIGURASI ELEMEN FASIH - DATA CLEANING SOSIAL EKONOMI (NIK)
# ==============================================================================

EXCEL_NIK_R29_COLUMNS_CONFIG = {
    # Kolom Identitas & Data Sosial Ekonomi (NIK) dari Excel
    "assignment_id": [
        "assignment_id", "assignment id", "id_assignment", "id assignment",
        "assignment", "id"
    ],
    "no_urut_kk": [
        "no_urut_kk", "no urut kk", "no_urut", "nourutkk",
        "no urut", "no_kk_urut", "urut_kk", "no_art"
    ],
    "nomor_induk_kependudukan": [
        "nomor_induk_kependudukan", "nik", "nomor induk kependudukan",
        "no_nik", "no nik", "nik_anggota", "nik_art"
    ],
    "url": [
        "url", "link_fasih_sm", "link",
        "link fasih", "link_fasih", "tautan"
    ],
    "nomor_kartu_keluarga": [
        "nomor_kartu_keluarga", "nomor kartu keluarga", "no_kk",
        "no kk", "nkk", "nomor_kk", "kartu_keluarga"
    ],
    "nama": [
        "nama", "nama_lengkap", "nama lengkap",
        "nama_anggota", "nama anggota", "nama_art"
    ],

    # Kolom Status & Keterangan Eksekusi
    "status": ["status_eksekusi", "status_proses", "status"],
    "keterangan": ["keterangan", "ket", "catatan_eksekusi"]
}

# ==============================================================================
# SELECTOR ELEMEN FORMULIR FASIH (CLEANING NIK)
# ==============================================================================

NIK_R29_SELECTORS = {
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

    # Rincian NIK DTSEN
    "container_nik": "div[id^='nik_dtsen#'], div[id*='nik_dtsen']",
    "input_nik": "input[type='text'], input",

    # Tombol Aksi Formulir & Dialog Submit
    "btn_kirim": "button#btn-kirim, button:has-text('Kirim')",
    "btn_konfirmasi_kirim": "div:has-text('Konfirmasi Kirim') button:has-text('Konfirmasi'), div:has-text('Apakah Anda yakin') button:has-text('Konfirmasi'), button:has-text('Konfirmasi')",
    "dialog_sukses": "div[role='alertdialog']:has-text('Assignment Berhasil Disubmit'), h2:has-text('Assignment Berhasil Disubmit'), p:has-text('Perubahan Anda berhasil disimpan'), div[role='dialog']:has-text('Berhasil')"
}

EXCEL_NIK_R29_COLUMNS_CONFIG = EXCEL_NIK_R29_COLUMNS_CONFIG
NIK_R29_SELECTORS = NIK_R29_SELECTORS


EXCEL_NIK_COLUMNS_CONFIG = EXCEL_NIK_R29_COLUMNS_CONFIG
NIK_SELECTORS = NIK_R29_SELECTORS
