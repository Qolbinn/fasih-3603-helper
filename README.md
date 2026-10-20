# FASIH 3603 Helper
*Suite Otomasi Survei & Sensus BPS Kabupaten Tangerang*

---

## 📌 Tentang Aplikasi
**FASIH 3603 Helper** adalah aplikasi desktop modern yang dirancang untuk mempermudah rekan-rekan kerja di lingkungan BPS Kabupaten Tangerang (kode wilayah: 3603) dalam menjalankan otomasi pembersihan data (*data cleaning*) dan pengolahan survei/sensus pada portal Fasih BPS.

Aplikasi ini didesain ramah pengguna non-teknis:
- **Zero-Terminal**: Tidak perlu membuka Command Prompt, PowerShell, atau editor kode.
- **One-Click Chrome Launcher & Auto SSO**: Meluncurkan browser dengan remote debugging dan mendeteksi sesi login SSO BPS secara otomatis sebelum eksekusi dimulai.
- **Validasi Template & Unduh Template**: Memeriksa kelengkapan kolom file Excel serta menyediakan tombol **Unduh Template** resmi lengkap dengan contoh format data.
- **Kontrol Zoom Tampilan**: Fitur perbesar/perkecil tampilan antarmuka (80% s.d. 140%) untuk kenyamanan di berbagai resolusi layar monitor.
- **2 Opsi Eksekusi Fleksibel**:
  - **Mode Produksi**: Langsung submit konfirmasi formulir secara otomatis untuk pemrosesan massal tanpa jeda.
  - **Mode Debug / Review Submit**: Mengisi semua data, memunculkan modal konfirmasi Fasih, lalu menunggu pengguna menekan **ENTER** atau tombol konfirmasi setelah memeriksa data.
- **Kontrol Jeda & Berhenti Responsif**: Tombol Jeda (Pause) dan Berhenti Aman (Stop) langsung merespons seketika tanpa menunggu sleep loop selesai.
- **Tampilan 2 Tab Interaktif**:
  - **Tab 1: Live Statistik & Rekap Data** (metrik, progress bar real-time, status baris aktif, dan tabel data live).
  - **Tab 2: Log Terminal** (catatan proses berwarna dengan fitur salin & auto-scroll).
- **Pengaman Sensus & Audit Trail**:
  - Menyimpan jejak audit per baris ke file CSV terpisah.
  - Checkpoint per baris langsung disimpan ke file Excel kerja.
  - Sesi SSO dipantau secara real-time; jika sesi berakhir, bot otomatis mem-pause dan memunculkan browser untuk re-login tanpa kehilangan progress.

---

## 📂 Struktur Proyek
```
Fasih 3603 Helper/
│
├── main.py                     # Entry point utama aplikasi desktop (CustomTkinter)
├── cli_runner.py               # Standalone runner CLI untuk uji paritas & debugging
├── config.py                   # Konfigurasi global, path AppData, flags Chrome
│
├── core/                       # Layanan inti bersama (Shared Services)
│   ├── browser_manager.py     # Deteksi path browser, port CDP 9222, status login SSO
│   ├── window_controller.py   # Pengendali minimize & restore jendela browser (Win32 API)
│   ├── audit_logger.py        # Pencatatan jejak audit per baris (CSV)
│   ├── logger.py              # Central logger (file harian + callback UI)
│   └── event_bus.py           # Antrian event thread-safe (Worker <-> UI)
│
├── modules/                    # Modul-modul otomasi (Hub Architecture)
│   ├── data_cleaning/         # Modul Utama: Data Cleaning SE2026
│   │   ├── selectors.py       # Semua CSS/XPath selector terpusat
│   │   ├── validator.py       # Validasi template & pembuat template Excel
│   │   ├── engine.py          # Logika Playwright data cleaning
│   │   └── view.py            # Tampilan CustomTkinter 2-Tab (Statistik & Log)
│   │
│   └── approve_se2026/        # Modul: Batch Approval SE 2026 (Segera Hadir)
│       └── view.py            # Tampilan Pratinjau Fitur Approval
│
└── build/                      # Berkas packaging & installer
    ├── build_exe.py           # Skrip build PyInstaller (--onedir)
    └── installer.iss          # Skrip Inno Setup Compiler (.exe setup installer)
```

---

## 🚀 Cara Menjalankan (Mode Pengembangan)

1. Pastikan environment Python aktif:
   ```powershell
   conda activate automation
   ```
2. Jalankan aplikasi desktop:
   ```powershell
   python main.py
   ```
3. Atau jalankan CLI runner (untuk debugging):
   ```powershell
   python cli_runner.py --file "path/to/flag_clean.xlsx"
   ```

---

## 📦 Cara Membangun Executable & Installer

1. **Build Folder Executable (PyInstaller)**:
   ```powershell
   python build/build_exe.py
   ```
   Hasil build akan tersimpan di folder `dist/FASIH_3603_Helper/`.

2. **Build Installer Windows (Inno Setup)**:
   - Buka aplikasi **Inno Setup Compiler**.
   - Buka file `build/installer.iss`.
   - Klik menu **Build -> Compile** (atau tekan `Ctrl + F9`).
   - File installer siap didistribusikan: `dist_installer/FASIH_3603_Helper_Setup_v1.0.exe`.

---

## 🔒 Kebijakan & Pengamanan
- Seluruh data lokal (profil Chrome terpisah, file log, dan jejak audit) tersimpan secara aman di folder:
  `%LOCALAPPDATA%\FASIH3603Helper\`
- Pembaruan aplikasi melalui installer baru tidak akan menghapus data konfigurasi atau riwayat kerja pengguna.
