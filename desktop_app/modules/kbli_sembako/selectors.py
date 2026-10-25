# ==============================================================================
# SELECTOR & KONFIGURASI ELEMEN FASIH - KBLI SEMBAKO SE2026
# ==============================================================================

EXCEL_KBLI_SEMBAKO_COLUMNS_CONFIG = {
    # Kolom Identitas & Data KBLI dari Excel
    "keg_utama": [
        "keg_utama", "kegiatan utama", "kegiatan_utama",
        "keg_utama_fasih", "kegiatan", "uraian_kegiatan", "uraian kegiatan"
    ],
    "kbli_akhir": [
        "kbli_akhir", "kbli akhir", "kbli",
        "kbli_lama", "kbli_awal", "kode_kbli_akhir"
    ],
    "url": [
        "url", "link_fasih_sm", "link",
        "link fasih", "link_fasih", "tautan"
    ],
    "status_kbli": [
        "status_kbli", "status kbli", "status_kbli_fasih",
        "status kbli fasih", "status_verifikasi_kbli"
    ],
    "kbli_terbaru": [
        "kbli_terbaru", "kbli terbaru", "kbli_baru",
        "kbli baru", "kbli_rekomendasi", "kode_kbli_terbaru"
    ],

    # Kolom Status & Keterangan Eksekusi
    "status": ["status_eksekusi", "status_proses", "status"],
    "keterangan": ["keterangan", "ket", "catatan_eksekusi"]
}

# ==============================================================================
# SELECTORS ELEMEN FORMULIR FASIH (KBLI SEMBAKO)
# ==============================================================================

KBLI_SEMBAKO_SELECTORS = {
    # Sidebar Navigation Selectors
    "sidebar_blok_ii": "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')] | //*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')]",
    "sidebar_keterangan_usaha": "xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[@title='Keterangan Usaha/Perusahaan' or text()='Keterangan Usaha/Perusahaan']",
    "sidebar_sub_usaha_items": (
        "xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[@title='Keterangan Usaha/Perusahaan' or text()='Keterangan Usaha/Perusahaan']"
        "/following-sibling::div[starts-with(@id, 'collapsible-')]"
        "//div[contains(@class, 'border-l-2')]/div[contains(@class, 'fasih-form-sidebar')]"
        "/div[contains(@class, 'cursor-pointer') and @title and not(contains(@title, 'Keterangan Usaha/Perusahaan')) and not(contains(@title, 'BLOK II'))]"
    ),
    "sidebar_blok_catatan": "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='CATATAN' or normalize-space(text())='CATATAN' or contains(text(), 'CATATAN')] | //*[@title='CATATAN' or normalize-space(text())='CATATAN']",

    # Rincian Kegiatan Utama
    "field_kegiatan_utama": "div[id^='keg_utama#'] input[type='text'], div[id^='keg_utama#'] textarea, div[id*='keg_utama'] input",

    # Rincian Karakteristik Usaha Sembako (13. b1, 13. b2, 13. b3, 13. c)
    "container_produk_sendiri": "div[id^='produk_sendiri#'], div[id='produk_sendiri']",
    "container_layanan_mamin": "div[id^='layanan_mamin#'], div[id='layanan_mamin']",
    "container_keg_penjualan": "div[id^='keg_penjualan#'], div[id='keg_penjualan']",
    "container_lokasi_usaha": "div[id^='lokasi_usaha#'], div[id='lokasi_usaha']",

    # Rincian KBLI GenAI (Radio Group)
    "container_kbli_genai": "div[id^='kbli_genai#']",
    "radio_master_kbli": "label:has-text('Pilih dari Master KBLI'), div[role='group']:has(input[value='999999']), div[role='radio']:has(+ label:has-text('Pilih dari Master KBLI')), input[value='999999']",

    # Rincian Pilih dari Master KBLI (Muncul saat Master KBLI dipilih)
    "container_master_kbli": "div[id^='kbli#'], div[id='kbli']",
    "textarea_master_kbli": "textarea, input[type='text'], input",
    "btn_reset_master_kbli": "button[aria-label='Reset'], button:has-text('Reset')",
    "btn_dropdown_master_kbli": "button[aria-haspopup='dialog'], button[aria-haspopup='listbox']",

    # Modal Catatan (Remarks)
    "btn_catatan": "button[title='Catatan'], button[aria-label='Catatan']",

    # Rincian Produk Halal (19.a & 19.c)
    "container_halal": "div[id^='halal#'], div[id='halal']",
    "container_belum_halal": "div[id^='belum_halal#'], div[id='belum_halal']",
    "input_belum_halal": "input[type='text'], input[inputmode='numeric'], input",

    # Rincian Izin Edar BPOM (20.a & 20.c)
    "container_izin_edar": "div[id^='izin_edar#'], div[id='izin_edar']",
    "container_belum_bpom": "div[id^='belum_bpom#'], div[id='belum_bpom']",
    "input_belum_bpom": "input[type='text'], input[inputmode='numeric'], input",

    # Submit & Konfirmasi Flow
    "btn_kirim": "button#btn-kirim, button:has-text('Kirim')",
    "btn_konfirmasi_kirim": "div:has-text('Konfirmasi Kirim') button:has-text('Konfirmasi'), div:has-text('Apakah Anda yakin') button:has-text('Konfirmasi'), button:has-text('Konfirmasi')",
    "dialog_sukses": "div[role='alertdialog']:has-text('Assignment Berhasil Disubmit'), h2:has-text('Assignment Berhasil Disubmit'), p:has-text('Perubahan Anda berhasil disimpan')"
}
