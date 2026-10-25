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
├── desktop_app/                 # Aplikasi Desktop Python (CustomTkinter + Playwright)
│   ├── main.py                  # Entry point utama aplikasi desktop
│   ├── cli_runner.py            # Standalone runner CLI untuk uji paritas & debugging
│   ├── config.py                # Konfigurasi global, path AppData, flags Chrome
│   ├── core/                    # Shared Services (BrowserManager, Logger, EventBus)
│   ├── modules/                 # Modul Otomasi Desktop (Cleaning Usaha, KBLI, NIK)
│   ├── assets/                  # Ikon aplikasi & gambar branding
│   └── build/                   # Skrip PyInstaller & Inno Setup Compiler
│
└── browser_extension/           # Ekstensi Browser Native (Manifest V3 - Chrome / Edge)
    ├── manifest.json            # Konfigurasi ekstensi MV3
    ├── background/              # Service worker (Side Panel & message dispatcher)
    ├── sidepanel/               # Pusat Komando (UI Side Panel, Orchestrator, Excel IO)
    ├── content/                 # Content Scripts & DOM Toolkit per tab Fasih
    ├── libs/                    # Vendor library (SheetJS / xlsx)
    └── icons/                   # Aset ikon ekstensi
```

---

# FASIH 3603 Helper
*Suite Otomasi Pembersihan Data & KBLI Survei BPS Kabupaten Tangerang*

---

## 📌 Tentang Aplikasi & Arsitektur
**FASIH 3603 Helper** adalah suite otomasi resmi yang dirancang khusus untuk mempermudah rekan-rekan kerja di lingkungan **BPS Kabupaten Tangerang (kode wilayah: 3603)** dalam menjalankan verifikasi anomali, pembersihan data (*data cleaning*), penyesuaian KBLI, dan administrasi survei/sensus pada portal Fasih BPS.

Untuk fleksibilitas maksimal dan ketahanan terhadap proteksi bot web server, repositori ini kini menyediakan **2 varian eksekusi**:

1. **🌐 Browser Extension (Chrome / Edge Manifest V3 - Direkomendasikan)**:
   - **Native & Anti-Detection**: Dijalankan langsung di browser harian pengguna tanpa flag remote debugging CDP (`--remote-debugging-port`), sehingga sidik jari browser (*fingerprint*) adalah browser manusia asli non-automasi.
   - **Pusat Komando Side Panel**: Antarmuka terintegrasi di panel samping browser Chrome/Edge tanpa perlu instalasi Python runtime di komputer pengguna.
   - **Multi-Tab Worker Paralel**: Mendukung pemrosesan data konkuren (1 hingga 3 tab bersamaan) yang dikomandoi dari satu antrean data Excel.
   - **Offline-Ready Excel Engine**: Membaca dan memperbarui file Excel secara instan di memori peramban via SheetJS tanpa server eksternal.

2. **🖥️ Desktop App (Python + CustomTkinter + Playwright)**:
   - Aplikasi desktop mandiri (tersedia skrip build PyInstaller & Windows Installer Inno Setup).
   - Seluruh modul, selektor, logika retry, dan audit log tersimpan rapi di dalam direktori `desktop_app/`.

---

## 📂 Struktur Repositori
```
Fasih 3603 Helper/
│
├── browser_extension/            # 🌐 Ekstensi Browser Native (Manifest V3)
│   ├── manifest.json             # Deklarasi Manifest V3, perizinan & content scripts
│   ├── background/
│   │   └── service_worker.js     # Background worker & penanganan Side Panel
│   ├── sidepanel/                # Pusat Komando Side Panel
│   │   ├── sidepanel.html        # Layout UI modern (Metrik, Antrean, Log)
│   │   ├── sidepanel.css         # Styling tema resmi BPS Tangerang
│   │   ├── sidepanel.js          # Controller UI & drag-and-drop Excel
│   │   ├── orchestrator.js       # Multi-tab worker pool & state management
│   │   ├── excel_io.js           # Parser & updater Excel (SheetJS)
│   │   └── modules_config.js     # Konfigurasi kolom & alias per modul
│   ├── content/                  # Eksekusi DOM pada Tab Fasih
│   │   ├── fh_namespace.js       # Global state & logger content script
│   │   ├── dom_toolkit.js        # Human-like typing, click, modal, switch, remarks
│   │   ├── session_guard.js      # Detektor sesi login SSO BPS real-time
│   │   ├── content_main.js       # Dispatcher perintah per tab
│   │   └── tasks/                # Runner per modul otomasi:
│   │       ├── remark_kbli.task.js      # Remark KBLI SE2026 (#0 / #4)
│   │       ├── kbli_sembako.task.js     # KBLI 47111 vs 47211 Minimarket/Kelontong
│   │       ├── kbli_pmm.task.js         # Penyedia Mamin (56101 vs 56102, 13b/13c)
│   │       ├── cleaning_usaha.task.js   # Cleaning Pengeluaran, Pendapatan, Aset
│   │       ├── cleaning_nik_r30.task.js # Verifikasi NIK ART KK (#3)
│   │       └── cleaning_nik_r27.task.js # Pembersihan NIK ART Menyeluruh (#0)
│   ├── libs/
│   │   └── xlsx.full.min.js      # SheetJS library standalone (offline)
│   ├── icons/                    # Aset ikon resolusi 16, 32, 48, 128 px
│   └── Pack_Extension.ps1        # Skrip otomatis kemas ekstensi ke file ZIP
│
└── desktop_app/                  # 🖥️ Aplikasi Desktop Python (Existing Suite)
    ├── main.py                   # Entry point aplikasi GUI desktop
    ├── cli_runner.py             # Runner mode CLI untuk pengujian
    ├── config.py                 # Konfigurasi browser & AppData
    ├── core/                     # Shared services (BrowserManager, Logger, EventBus)
    ├── modules/                  # Logika modul Python (Cleaning, KBLI, NIK)
    ├── assets/                   # Ikon & logo desktop app
    ├── build/                    # build_exe.py & installer.iss
    └── *.bat                     # Batch launcher siap pakai
```

---

## 🌐 Panduan Memasang Ekstensi Browser

### 1. Pasang di Google Chrome atau Microsoft Edge
1. Buka browser **Google Chrome** atau **Microsoft Edge**.
2. Buka menu ekstensi:
   - Chrome: ketik `chrome://extensions` di address bar, lalu aktifkan toggle **Mode Pengembang (Developer Mode)** di pojok kanan atas.
   - Edge: ketik `edge://extensions` di address bar, lalu aktifkan toggle **Mode Pengembang**.
3. Klik tombol **Muat yang belum dibongkar (Load Unpacked)**.
4. Pilih folder `browser_extension` yang berada di dalam repositori ini.
5. Ekstensi **FASIH 3603 Helper** akan terpasang seketika.

### 2. Membuka dan Menggunakan Side Panel
1. Buka situs [https://fasih-sm.bps.go.id](https://fasih-sm.bps.go.id) dan pastikan akun SSO BPS Anda sudah dalam kondisi login aktif.
2. Klik ikon puzzle ekstensi di toolbar kanan atas browser, lalu pin ikon **FASIH 3603 Helper**.
3. Klik ikon ekstensi untuk membuka **Side Panel** di sisi kanan peramban.
4. Pilih **Modul Otomasi** yang ingin dijalankan.
5. Pilih **Multi-Tab Worker** (1 Tab direkomendasikan, atau 2-3 Tab untuk pemrosesan paralel).
6. Tentukan **Mode Eksekusi**:
   - **Produksi**: Formulir langsung dikonfirmasi dan disubmit secara otomatis.
   - **Review**: Mengisi data dan memunculkan konfirmasi agar dapat diperiksa manual sebelum dikirim.
7. Unggah file Excel sasaran (tersedia tombol **Unduh Template** resmi jika belum memiliki format baku).
8. Klik **Mulai Otomasi**. Anda dapat menjeda (*Pause*), melanjutkan (*Resume*), atau menghentikan (*Stop*) kapan saja.
9. Setelah selesai, klik **Unduh Hasil Excel** untuk mengunduh rekap status baris yang berhasil/gagal.

### 3. Mengemas Ekstensi untuk Distribusi (.zip)
Untuk membagikan ekstensi kepada staf atau mitra tanpa perlu clone git:
```powershell
powershell -ExecutionPolicy Bypass -File "browser_extension\Pack_Extension.ps1"
```
File `Fasih_3603_Helper_Extension.zip` siap dibagikan dan dapat langsung diekstrak lalu di-load oleh pengguna lain.

---

## 🖥️ Panduan Aplikasi Desktop (Python)

### 1. Menjalankan di Mode Pengembangan
```powershell
cd desktop_app
conda activate automation
python main.py
```

### 2. Membangun Executable & Installer Windows
1. **PyInstaller**:
   ```powershell
   cd desktop_app
   python build/build_exe.py
   ```
2. **Inno Setup**: Buka `desktop_app/build/installer.iss` menggunakan Inno Setup Compiler dan tekan `Ctrl + F9`.

---

## 🔒 Kebijakan & Pengamanan
- Seluruh komunikasi data, parsing Excel, dan otomasi berjalan 100% secara lokal pada komputer pengguna tanpa perantara server pihak ketiga.
- Ekstensi dilengkapi **Session Guard** yang mendeteksi kedaluwarsa sesi SSO BPS dan langsung menjeda otomasi secara aman agar pengguna dapat login kembali tanpa kehilangan antrean data.
