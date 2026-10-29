# 🚀 FASIH 3603 Helper
*Suite Otomasi Survei, Pembersihan Data (Data Cleaning), & Verifikasi KBLI*  
**Badan Pusat Statistik (BPS) Kabupaten Tangerang (Kode Wilayah: 3603)**

---

## 📌 Daftar Isi
1. [Tentang Aplikasi & Arsitektur](#-tentang-aplikasi--arsitektur)
2. [Panduan Cepat Pengguna Baru (Quick Start Workflow)](#-panduan-cepat-pengguna-baru-quick-start-workflow)
3. [Kamus Standar Kode Catatan / Remarks BPS](#-kamus-standar-kode-catatan--remarks-bps)
4. [Penjelasan Mendalam Algoritma & Logika per Modul (Lengkap dengan Flowchart)](#-penjelasan-mendalam-algoritma--logika-per-modul-lengkap-dengan-flowchart)
   - [4.1. 🌾 Modul KBLI Kategori A SE2026 (`kbli_kategori_A`)](#41--modul-kbli-kategori-a-se2026-kbli_kategori_a)
   - [4.2. 📦 Modul KBLI PMM SE2026 (Penyedia Makan Minum) (`kbli_pmm`)](#42--modul-kbli-pmm-se2026-penyedia-makan-minum-kbli_pmm)
   - [4.3. 🛒 Modul KBLI Sembako SE2026 (`kbli_sembako`)](#43--modul-kbli-sembako-se2026-kbli_sembako)
   - [4.4. 🏷️ Modul Remark KBLI SE2026 (Umum) (`remark_kbli`)](#44-️-modul-remark-kbli-se2026-umum-remark_kbli)
   - [4.5. 🧹 Modul Cleaning Usaha SE2026 (`cleaning_usaha`)](#45--modul-cleaning-usaha-se2026-cleaning_usaha)
   - [4.6. 🆔 Modul Cleaning NIK R30 SE2026 (Anggota Keluarga / ART) (`cleaning_nik_r30`)](#46--modul-cleaning-nik-r30-se2026-anggota-keluarga--art-cleaning_nik_r30)
   - [4.7. 🆔 Modul Cleaning NIK R29 SE2026 (Penanggung Jawab Usaha) (`cleaning_nik_r29`)](#47--modul-cleaning-nik-r29-se2026-penanggung-jawab-usaha-cleaning_nik_r29)
   - [4.8. 🆔 Modul Cleaning NIK R27 SE2026 (Pemilik Usaha) (`cleaning_nik_r27`)](#48--modul-cleaning-nik-r27-se2026-pemilik-usaha-cleaning_nik_r27)
   - [4.9. ✅ Modul Approve SE2026 (PML / Taskforce) (`approve_se2026`)](#49--modul-approve-se2026-pml--taskforce-approve_se2026)
5. [Fitur Keamanan, Anti-Detection, & Penanganan Sesi SSO](#-fitur-keamanan-anti-detection--penanganan-sesi-sso)
6. [Panduan Instalasi & Build Installer Windows](#-panduan-instalasi--build-installer-windows)

---

## 🏛️ Tentang Aplikasi & Arsitektur

**FASIH 3603 Helper** dirancang khusus untuk mempermudah, menstandarkan, dan mengotomasi penjaminan kualitas data survei dan sensus (seperti **Sensus Ekonomi SE2026**) pada portal **Fasih BPS** ([https://fasih-sm.bps.go.id](https://fasih-sm.bps.go.id)).

Aplikasi ini tersedia dalam **2 varian eksekusi**:

| Komponen | 🖥️ Desktop App (Python + Playwright) | 🌐 Browser Extension (Chrome/Edge MV3) |
| :--- | :--- | :--- |
| **Bentuk** | Aplikasi Windows mandiri (`.exe` installer) | Ekstensi browser di toolbar Google Chrome / MS Edge |
| **Pusat Kontrol** | Antarmuka grafis kaya fitur (CustomTkinter) | Panel samping (*Side Panel*) berdampingan dengan tab web |
| **Kapasitas** | Multi-Worker paralel (1 s.d. 5 worker konkuren) | Multi-Tab Worker (1 s.d. 3 tab browser konkuren) |
| **Instalasi Python** | **Tidak perlu** (cukup jalankan file setup installer) | **Tidak perlu** (cukup muat folder ekstensi) |
| **Tujuan Utama** | Pengolahan data massal ribuan baris otomatis | Operasional harian fleksibel semi-manual / inspeksi cepat |

---

## 🚦 Panduan Cepat Pengguna Baru (Quick Start Workflow)

```mermaid
flowchart TD
    A["1. Luncurkan Browser & Login SSO"] --> B["2. Pilih Modul & Unduh Template"]
    B --> C["3. Salin Data ke Excel & Tutup File"]
    C --> D["4. Muat File ke Aplikasi & Cek Tabel"]
    D --> E["5. Tentukan Mode & Jumlah Worker"]
    E --> F["6. Klik 'Mulai Otomasi' & Monitor Live"]
```

1. **Langkah 1: Siapkan Browser & Sesi Login**:
   - Buka aplikasi **FASIH 3603 Helper**.
   - Klik tombol **🌐 Buka Browser** pada bilah atas aplikasi (atau buka Chrome normal).
   - Masuk ke portal [https://fasih-sm.bps.go.id](https://fasih-sm.bps.go.id) dan pastikan akun SSO BPS Anda telah login aktif.
2. **Langkah 2: Pilih Modul & Unduh Template**:
   - Pilih menu modul yang sesuai di sidebar kiri (misal: *KBLI Kategori A*).
   - Klik tombol **📥 Unduh Template** untuk mendapatkan format Excel resmi dengan header standar.
3. **Langkah 3: Salin Data & Tutup Excel**:
   - Isi baris data penugasan Anda ke dalam template tersebut.
   - **PENTING**: Simpan dan **tutup (*close*)** file Excel di komputer Anda sebelum memulai otomasi agar sistem operasi tidak mengunci file saat bot hendak menulis status hasil eksekusi.
4. **Langkah 4: Muat File Excel ke Aplikasi**:
   - Klik **📂 Pilih File**, pilih file Excel Anda.
   - Aplikasi akan otomatis memvalidasi struktur kolom dan menampilkan baris data pada tabel pratinjau (*Live Table*).
5. **Langkah 5: Tentukan Mode Eksekusi**:
   - **Mode Produksi**: Bot langsung mengisi formulir, mengonfirmasi modal, dan mengirimkan (*submit*) data secara otomatis tanpa interupsi.
   - **Mode Debug / Review Submit**: Bot mengisi formulir dan memunculkan pop-up konfirmasi kirim, lalu **berhenti menunggu tinjauan Anda**. Anda cukup menekan tombol **ENTER** pada keyboard jika data sudah sesuai untuk lanjut ke baris berikutnya.
6. **Langkah 6: Mulai Otomasi**:
   - Klik **▶️ Mulai Otomasi**. Pantau progres melalui kartu metrik, status baris tabel, dan tab **Log Terminal**. Anda dapat mengklik **⏸️ Jeda** atau **⏹️ Berhenti Aman** kapan saja.

---

## 🏷️ Kamus Standar Kode Catatan / Remarks BPS

Pada formulir Fasih SE2026, setiap field yang mengalami penyesuaian atau verifikasi wajib dibubuhi kode catatan (*remarks*) melalui tombol **Catatan** di samping rincian maupun di menu sidebar **CATATAN**:

| Kode Remark | Arti Standar BPS | Modul yang Menggunakan | Kapan Kode Ini Dipakai? |
| :---: | :--- | :--- | :--- |
| **`#0`** | **Data Tetap / Terkonfirmasi Valid** | `kbli_kategori_A`<br>`kbli_pmm`<br>`kbli_sembako`<br>`remark_kbli`<br>`cleaning_usaha`<br>`cleaning_nik_r27` | Ketika isian formulir lapangan diperiksa dan sudah sesuai (Status KBLI "Tetap", nilai finansial sama, atau identitas pemilik usaha valid tanpa koreksi). |
| **`#3`** | **Klarifikasi NIK Kependudukan** | `cleaning_nik_r30` | Khusus pada Rincian 30 NIK Anggota Rumah Tangga (ART) yang telah ditelusuri ke dokumen keluarga / kartu keluarga / dinas dukcapil. |
| **`#4`** | **Koreksi / Perubahan Data** | `kbli_kategori_A`<br>`kbli_pmm`<br>`kbli_sembako`<br>`remark_kbli`<br>`cleaning_usaha` | Ketika kode KBLI diganti dengan kode baru, atau ketika komponen pengeluaran/pendapatan usaha diperbaiki dari nilai aslinya. |

---

## 🧠 Penjelasan Mendalam Algoritma & Logika per Modul (Lengkap dengan Flowchart)

---

### 4.1. 🌾 Modul KBLI Kategori A SE2026 (`kbli_kategori_A`)

#### A. Latar Belakang & Tujuan
Menangani anomali unit usaha pada **Kategori A** (Pertanian, Kehutanan, dan Perikanan) serta unit **Jasa Pertanian/Perikanan**. Modul ini mengotomasi pengisian 4 rincian karakteristik usaha (13. b1 s.d. 13. b4), penanganan sertifikat halal & BPOM, serta penyesuaian KBLI.

#### B. Kolom Excel yang Dibutuhkan
* Wajib: `keg_utama`, `kbli_akhir`, `url`, `Status_KBLI`, `KBLI_Terbaru`
* Opsional: `Status_Eksekusi`, `Keterangan`

#### C. Diagram Alur Logika (Flowchart):
```mermaid
flowchart TD
    Start["Buka URL Penugasan Fasih"] --> ExpandBlok2["Buka Sidebar: Blok II -> Keterangan Usaha"]
    ExpandBlok2 --> FindUsaha["Cari Usaha yang cocok dengan 'keg_utama' di Excel"]
    FindUsaha -->|Tidak Ditemukan| Skip["Tandai Baris: DILEWATI di Excel"]
    FindUsaha -->|Cocok| Step13b1["13. b1 (Produksi Sendiri) -> 2. Tidak (value='2')"]
    Step13b1 --> Step13b2["13. b2 (Layanan Mamin) -> 2. Tidak (value='2')"]
    Step13b2 --> Step13b3["13. b3 (Penjualan Barang) -> 2. Tidak (value='2')"]
    Step13b3 --> DetectJasa{"Cek kata 'jasa' pada keg_utama (regex '\\bjasa\\b')"}
    DetectJasa -->|Ada kata Jasa| OptJasa["13. b4 -> 1. Jasa (value='1')"]
    DetectJasa -->|Non-Jasa| OptAgri["13. b4 -> 2. Pertanian, Perikanan, Kehutanan (value='2')"]
    OptJasa --> CheckHalalBPOM["Cek Rincian Halal & BPOM"]
    OptAgri --> CheckHalalBPOM
    CheckHalalBPOM --> EvalKBLI{"Nilai Status_KBLI di Excel?"}
    EvalKBLI -->|Tetap| FlowTetap["Pastikan KBLI sesuai kbli_akhir. Beri Catatan '#0'"]
    EvalKBLI -->|Ganti| FlowGanti["Pilih KBLI Baru (GenAI / Master). Beri Catatan '#4'"]
    FlowTetap --> AddSidebarNote["Menu Sidebar CATATAN -> Tambah '#0'"]
    FlowGanti --> AddSidebarNote4["Menu Sidebar CATATAN -> Tambah '#4'"]
    AddSidebarNote --> SubmitForm["Kirim & Konfirmasi Formulir"]
    AddSidebarNote4 --> SubmitForm
```

#### D. Detail Aturan Percabangan:
1. **Deteksi Kata Kunci Jasa (13. b4)**:
   - Bot memeriksa nilai `keg_utama` menggunakan pencarian kata *whole-word* `\bjasa\b` secara *case-insensitive*.
   - **Memilih `1. Jasa` (`value="1"`)** jika kegiatan utama berupa: *JASA PENGGILINGAN PADI*, *Jasa air taman atau menyiram tanaman*, *JASA PEMOTONGAN POHON DAN JUAL KAYU*, *JASA PENEBANGAN POHON*, *Jasa angkut hasil pertanian*, *Jasa tanam benih padi*, *Jasa penyewaan traktor*, *JASA PENYEDIAAN TEMPAT PEMANCINGAN IKAN*, dsb.
   - **Memilih `2. Pertanian, Perikanan, dan Kehutanan` (`value="2"`)** jika kegiatan utama non-jasa: *Pertanian Padi Sawah*, *Budidaya Ikan Lele*, *Perkebunan Kelapa Sawit*, *Peternakan Ayam*, dsb.
2. **Karakteristik 13. b1, 13. b2, 13. b3**:
   - Seluruhnya otomatis disetel ke **`2. Tidak`** (`value="2"`).
3. **Produk Halal & Izin Edar BPOM**:
   - Jika elemen rincian sertifikasi halal/BPOM muncul di halaman dan belum memiliki pilihan aktif, bot otomatis memilih opsi **`3. Tidak/Belum`** untuk menghindari galat validasi submit.
4. **KBLI & Catatan**:
   - **Tetap**: Memvalidasi kode lama, membubuhkan catatan `#0` pada elemen KBLI GenAI, Master KBLI, dan menu sidebar CATATAN.
   - **Ganti**: Memilih kode KBLI baru (jika tidak ada di opsi GenAI, bot otomatis memilih opsi *Pilih dari Master KBLI*, mengetikkan kode baru, dan memilih dari popover dropdown), lalu membubuhkan catatan `#4` di elemen KBLI dan sidebar CATATAN.

---

### 4.2. 📦 Modul KBLI PMM SE2026 (Penyedia Makan Minum) (`kbli_pmm`)

#### A. Latar Belakang & Tujuan
Menangani klasifikasi usaha **Penyediaan Makanan dan Minuman (PMM)** seperti restoran, rumah makan, warung makan, kafe, katering, kedai tenda, dan pedagang keliling. Memisahkan antara usaha restoran/tempat menetap (**56101**) dan kedai keliling/kaki lima (**56102**).

#### B. Kolom Excel yang Dibutuhkan
* Wajib: `keg_utama`, `kbli_akhir` (diisi 56101 atau 56102), `url`, `Status_KBLI`, `KBLI_Terbaru`
* Opsional: `Status_Eksekusi`, `Keterangan`

#### C. Diagram Alur Logika (Flowchart):
```mermaid
flowchart TD
    Start["Buka URL Penugasan Fasih"] --> OpenBlok2["Buka Sidebar: Blok II Keterangan Usaha"]
    OpenBlok2 --> MatchUsaha["Cari Usaha yang cocok dengan 'keg_utama' di Excel"]
    MatchUsaha -->|Tidak Cocok| SkipPMM["Tandai Baris: DILEWATI di Excel"]
    MatchUsaha -->|Cocok| Step13b1["13. b1 (Produksi Sendiri) -> 2. Tidak (value='2')"]
    Step13b1 --> Step13b2["13. b2 (Layanan Mamin) -> 1. Ya (value='1')"]
    Step13b2 --> CheckKBLI{"Cek kbli_akhir di Excel"}
    CheckKBLI -->|56101| LocResto["13. c -> 9. Restoran, warung makan (value='09')"]
    CheckKBLI -->|56102| CheckWarn{"Ada pesan peringatan Usaha Keliling R.9a=2?"}
    CheckWarn -->|Ada Peringatan| LocKeliling["13. c -> 10. Keliling (value='10')"]
    CheckWarn -->|Tidak Ada| LocKedai["13. c -> 5. Kedai, stan, tenda (value='05')"]
    LocResto --> CheckHalalBPOM["Cek Rincian Halal & BPOM (Set '3. Tidak' jika kosong)"]
    LocKeliling --> CheckHalalBPOM
    LocKedai --> CheckHalalBPOM
    CheckHalalBPOM --> StatusKBLI{"Status_KBLI di Excel?"}
    StatusKBLI -->|Tetap| FlowTetap["Verifikasi KBLI eksisting. Beri Catatan '#0'"]
    StatusKBLI -->|Ganti| FlowGanti["Pilih KBLI Baru (GenAI / Master). Beri Catatan '#4'"]
    FlowTetap --> NoteSidebar["Buka Menu CATATAN -> Tambah '#0'"]
    FlowGanti --> NoteSidebar4["Buka Menu CATATAN -> Tambah '#4'"]
    NoteSidebar --> SubmitForm["Kirim & Konfirmasi Formulir"]
    NoteSidebar4 --> SubmitForm
```

#### D. Detail Aturan Percabangan:
1. **Pengisian Karakteristik Usaha PMM**:
   - **13. b1** (Memproduksi barang di lokasi ini?): Pilih **`2. Tidak`** (`value="2"`).
   - **13. b2** (Menyediakan layanan makan dan minum?): Pilih **`1. Ya`** (`value="1"`).
   - Mengisi rincian **13. c (Aktivitas utama penyediaan mamin)** yang muncul dinamis berdasarkan `kbli_akhir`:
     - **Jika `kbli_akhir == "56101"`**: Memilih opsi **`9. Restoran, warung makan, dan sejenisnya`** (`value="09"`).
     - **Jika `kbli_akhir == "56102"`**: Memilih opsi **`5. Kedai, stan, tenda`** (`value="05"`).
     - **Aturan Pengecualian Usaha Keliling**: Jika terdeteksi peringatan/anomali *"Jika R.9a diisi kode 2 (Usaha Keliling), maka R.13c diisi kode 10"*, bot otomatis memilih opsi **`10. Keliling`** (`value="10"`).
2. **Pengecekan Sertifikasi Halal & BPOM**:
   - Jika rincian sertifikasi halal/BPOM tersedia dan belum terpilih, disetel ke **`3. Tidak/Belum`**.
3. **Verifikasi KBLI & Remarks**:
   - Jika `Status_KBLI == "Tetap"`: Memvalidasi kode eksisting dan menulis catatan `#0` pada GenAI, Master KBLI, dan sidebar CATATAN.
   - Jika `Status_KBLI == "Ganti"`: Memilih kode `KBLI_Terbaru` (via GenAI / Master KBLI) dan menulis catatan `#4`.

---

### 4.3. 🛒 Modul KBLI Sembako SE2026 (`kbli_sembako`)

#### A. Latar Belakang & Tujuan
Menangani anomali perdagangan eceran sembako dan bahan pokok. Mengoreksi dan memisahkan unit usaha minimarket/toko modern (**KBLI 47111**) dengan toko kelontong tradisional / warung sembako / toko beras (**KBLI 47211**).

#### B. Kolom Excel yang Dibutuhkan
* Wajib: `keg_utama`, `kbli_akhir`, `url`, `Status_KBLI`, `KBLI_Terbaru`
* Opsional: `Status_Eksekusi`, `Keterangan`

#### C. Diagram Alur Logika (Flowchart):
```mermaid
flowchart TD
    Start["Buka URL Penugasan Fasih"] --> OpenBlok2["Buka Sidebar: Blok II Keterangan Usaha"]
    OpenBlok2 --> MatchUsaha["Cari Usaha yang cocok dengan 'keg_utama' di Excel"]
    MatchUsaha -->|Tidak Cocok| SkipSembako["Tandai Baris: DILEWATI di Excel"]
    MatchUsaha -->|Cocok| Step13b1["13. b1 (Produksi Sendiri) -> 2. Tidak (value='2')"]
    Step13b1 --> Step13b2["13. b2 (Layanan Mamin) -> 2. Tidak (value='2')"]
    Step13b2 --> Step13b3["13. b3 (Kegiatan Penjualan) -> 1. Ya (value='1')"]
    Step13b3 --> Step13c["13. c (Lokasi Usaha) -> 4. Toko, ruko, dan sejenisnya (value='04')"]
    Step13c --> CheckHalalBPOM["Cek Rincian Halal & BPOM (Set '3. Tidak' jika kosong)"]
    CheckHalalBPOM --> StatusKBLI{"Status_KBLI di Excel?"}
    StatusKBLI -->|Tetap| FlowTetap["Tetapkan KBLI 47111 / 47211. Beri Catatan '#0'"]
    StatusKBLI -->|Ganti| FlowGanti["Pilih KBLI Baru (GenAI / Master). Beri Catatan '#4'"]
    FlowTetap --> NoteSidebar["Buka Menu CATATAN -> Tambah '#0'"]
    FlowGanti --> NoteSidebar4["Buka Menu CATATAN -> Tambah '#4'"]
    NoteSidebar --> SubmitForm["Kirim & Konfirmasi Formulir"]
    NoteSidebar4 --> SubmitForm
```

#### D. Detail Aturan Percabangan:
1. **Pengisian Karakteristik Usaha Sembako**:
   - **13. b1** (Memproduksi barang?): Pilih **`2. Tidak`** (`value="2"`).
   - **13. b2** (Layanan makan minum?): Pilih **`2. Tidak`** (`value="2"`).
   - **13. b3** (Melakukan kegiatan penjualan barang dagangan?): Pilih **`1. Ya`** (`value="1"`).
   - **13. c** (Lokasi usaha): Pilih **`4. Toko, ruko, dan sejenisnya`** (`value="04"`).
2. **Penyesuaian KBLI**:
   - Minimarket modern (Indomaret, Alfamart, dsb) -> diarahkan ke **47111**.
   - Toko sembako tradisional / warung beras -> diarahkan ke **47211**.
3. **Penyematan Catatan**: Menambahkan catatan `#0` jika KBLI tetap atau `#4` jika KBLI diganti pada elemen KBLI dan sidebar CATATAN.

---

### 4.4. 🏷️ Modul Remark KBLI SE2026 (Umum) (`remark_kbli`)

#### A. Latar Belakang & Tujuan
Modul generalis untuk memverifikasi dan mengubah kode KBLI di luar sektor khusus (seperti industri manufaktur, bengkel, toko pakaian, jasa transportasi, salon, properti, dll).

#### B. Kolom Excel yang Dibutuhkan
* Wajib: `keg_utama`, `kbli_akhir`, `url`, `Status_KBLI`, `KBLI_Terbaru`
* Opsional: `Status_Eksekusi`, `Keterangan`

#### C. Diagram Alur Logika (Flowchart):
```mermaid
flowchart TD
    Start["Buka URL Penugasan Fasih"] --> OpenBlok2["Buka Sidebar: Blok II Keterangan Usaha"]
    OpenBlok2 --> MatchUsaha["Cari Usaha yang cocok dengan 'keg_utama' di Excel"]
    MatchUsaha -->|Tidak Cocok| SkipRemark["Tandai Baris: DILEWATI di Excel"]
    MatchUsaha -->|Cocok| CheckActive["Periksa Kondisi KBLI Aktif di Web"]
    CheckActive --> DetectMode{"Mode Pilihan KBLI Web?"}
    DetectMode -->|Kondisi 1 - Master KBLI| ReadMaster["Baca teks kode KBLI di textarea Master KBLI"]
    DetectMode -->|Kondisi 2 - Radio GenAI| ReadRadio["Baca teks kode KBLI pada label Radio GenAI"]
    ReadMaster --> MatchCode{"Kode KBLI Web == 'kbli_akhir' Excel?"}
    ReadRadio --> MatchCode
    MatchCode -->|Tidak Cocok| SkipMismatch["Tandai Baris: DILEWATI (Perlu Verifikasi Manual)"]
    MatchCode -->|Cocok| StatusKBLI{"Status_KBLI di Excel?"}
    StatusKBLI -->|Tetap| RemarkTetap["Beri Catatan '#0' pada elemen KBLI GenAI & Master KBLI"]
    StatusKBLI -->|Ganti| ChangeKBLI{"KBLI_Terbaru ada di Radio GenAI?"}
    ChangeKBLI -->|Ada di GenAI| ClickGenAI["Pilih Radio GenAI target"]
    ChangeKBLI -->|Tidak Ada| UseMaster["Pilih 'Pilih dari Master KBLI' (999999) -> Ketik kode -> Pilih Popover"]
    ClickGenAI --> RemarkGanti["Beri Catatan '#4' pada elemen KBLI GenAI & Master KBLI"]
    UseMaster --> RemarkGanti
    RemarkTetap --> AddNoteSidebar0["Buka Menu CATATAN -> Tambah '#0'"]
    RemarkGanti --> AddNoteSidebar4["Buka Menu CATATAN -> Tambah '#4'"]
    AddNoteSidebar0 --> SubmitForm["Kirim & Konfirmasi Formulir"]
    AddNoteSidebar4 --> SubmitForm
```

#### D. Detail Aturan Percabangan:
1. **Pemeriksaan Kode KBLI Eksisting**:
   - Jika radio *Master KBLI* aktif: bot membaca textarea placeholder dan teks nilai KBLI.
   - Jika radio *GenAI* aktif: bot membaca teks label radio button.
   - Jika kode KBLI pada web tidak sama dengan `kbli_akhir` di Excel, bot tidak memaksakan perubahan, melainkan menandainya sebagai `DILEWATI` demi keamanan data.
2. **KBLI Tetap vs Ganti**:
   - Tetap: Mempertahankan kode dan memberi remark `#0`.
   - Ganti: Memilih kode baru dari radio GenAI; jika tidak ada, menggunakan pencarian Master KBLI (value `999999`), lalu memberi remark `#4`.

---

### 4.5. 🧹 Modul Cleaning Usaha SE2026 (`cleaning_usaha`)

#### A. Latar Belakang & Tujuan
Menangani anomali data finansial pada Blok II:
1. Rincian **Pengeluaran Usaha** (bahan baku, upah pekerja, sewa tempat, listrik/air, dll) beserta **Total Pengeluaran**.
2. Rincian **Pendapatan Usaha** (omset penjualan, jasa layanan, dll) beserta **Total Pendapatan**.
3. Rincian **Nilai Aset Modal** (aset bergerak, tidak bergerak, perlengkapan).

#### B. Kolom Excel yang Dibutuhkan
* Wajib: `url`, `Total_Pengeluaran`, `Total_Pendapatan`
* Komponen Rincian: `Pengeluaran_BahanBaku`, `Pengeluaran_Gaji`, `Pengeluaran_Sewa`, `Pengeluaran_Lainnya`, `Pendapatan_Penjualan`, `Pendapatan_Jasa`, `Nilai_Aset`
* Opsional: `Status_Eksekusi`, `Keterangan`

#### C. Diagram Alur Logika (Flowchart):
```mermaid
flowchart TD
    Start["Buka URL Penugasan Fasih"] --> OpenBlok2["Buka Blok II: Rincian Usaha Target"]
    OpenBlok2 --> ReadTotals["Baca Total Pengeluaran, Pendapatan, dan Aset saat ini di Web"]
    ReadTotals --> CompareTotals{"Apakah Total Finansial Web == Target Excel?"}
    CompareTotals -->|Total SAMA| KeepInputs["Nilai angka tidak diubah"]
    KeepInputs --> Remark0["Beri Catatan '#0' pada rincian Pengeluaran, Pendapatan, dan Aset"]
    CompareTotals -->|Total BERBEDA| OverwriteComponents["Timpa komponen rincian satu per satu (bahan baku, gaji, sewa, omset, dll)"]
    OverwriteComponents --> TriggerCalc["Picu kalkulasi ulang otomatis sistem Fasih"]
    TriggerCalc --> Remark4["Beri Catatan '#4' pada masing-masing rincian yang diubah"]
    Remark0 --> OpenCatatanSidebar["Buka Menu CATATAN di Sidebar"]
    Remark4 --> OpenCatatanSidebar
    OpenCatatanSidebar --> CheckAnomaliSwitch{"Switch 'Tampilkan Anomali Usaha dan Keluarga' sudah AKTIF?"}
    CheckAnomaliSwitch -->|Belum Aktif| TurnOnSwitch["Klik switch kontrol hingga aria-checked='true'"]
    CheckAnomaliSwitch -->|Sudah Aktif| WriteGenCatatan["Lanjut ke isian catatan"]
    TurnOnSwitch --> WriteGenCatatan
    WriteGenCatatan --> AddCatatanText["Tulis Catatan '#0' atau '#4' pada catatan umum"]
    AddCatatanText --> CheckGalat{"Apakah ada indikator galat merah?"}
    CheckGalat -->|Ada Galat| AbortSubmit["Batalkan Kirim (Gagal Validasi Formulir)"]
    CheckGalat -->|Tanpa Galat| SubmitForm["Klik Kirim -> Ringkasan Kirim -> Konfirmasi Kirim"]
```

#### D. Detail Aturan Percabangan:
1. **Perbandingan Total**:
   - Jika nilai total pada web sudah sama persis dengan angka target Excel, bot tidak menyentuh field angka (mencegah *dirty state* form yang tidak perlu) dan langsung membubuhkan catatan `#0`.
   - Jika terdapat selisih, bot mengisi rincian komponen pengeluaran/pendapatan, memicu event `input` dan `change`, lalu membubuhkan catatan `#4`.
2. **Aktivasi Toggle Anomali**:
   - Membuka menu sidebar CATATAN, mengecek elemen `div#cek_anomali_button`.
   - Mengaktifkan toggle switch hingga `aria-checked="true"` agar data anomali dapat terkonfirmasi di server pusat.

---

### 4.6. 🆔 Modul Cleaning NIK R30 SE2026 (Anggota Keluarga / ART) (`cleaning_nik_r30`)

#### A. Latar Belakang & Tujuan
Menangani data anomali kependudukan keluarga pada **Blok I (Keterangan Anggota Keluarga)**, khususnya **Rincian 30 (R30 - NIK Anggota Rumah Tangga)** yang terisi NIK dummy (seperti 000000..., 999999...), kurang dari 16 digit, atau perlu penegasan verifikasi lapangan.

#### B. Kolom Excel yang Dibutuhkan
* `no_urut_kk` (Nomor urut anggota keluarga: 1, 2, 3...)
* `nama_dtsen` (Nama lengkap anggota keluarga)
* `nik_fasih` (NIK yang tertera di Fasih saat ini)
* `nik_matched` (NIK hasil pemadanan data dukcapil/lapangan)
* `url` (Link penugasan Fasih)

#### C. Diagram Alur Logika (Flowchart):
```mermaid
flowchart TD
    Start["Buka URL Penugasan Fasih"] --> OpenBlok1["Buka Sidebar: Blok I (Keterangan Umum Keluarga)"]
    OpenBlok1 --> ExpandART["Buka Sub-menu: Keterangan Anggota Keluarga"]
    ExpandART --> FindMatchingART["Cari ART berdasarkan 'nama_dtsen' & 'no_urut_kk'"]
    FindMatchingART -->|ART Tidak Ditemukan| SkipART["Tandai Baris: DILEWATI di Excel"]
    FindMatchingART -->|ART Ditemukan| OpenARTPage["Buka Halaman Rincian ART Target"]
    OpenARTPage --> LocateR30["Temukan Rincian 30 (NIK ART: div#r30)"]
    LocateR30 --> CheckNIKInput{"Apakah NIK valid di Excel (16 digit angka)?"}
    CheckNIKInput -->|Ada Koreksi NIK| UpdateNIK["Kosongkan field lama, ketik NIK 16 digit baru"]
    CheckNIKInput -->|NIK Tetap| KeepNIK["Pertahankan isian NIK eksisting"]
    UpdateNIK --> AddRemarkR30["Klik tombol Catatan di Rincian 30 -> Tulis Catatan '#3'"]
    KeepNIK --> AddRemarkR30
    AddRemarkR30 --> OpenCatatanSidebar["Buka Menu CATATAN di Sidebar"]
    OpenCatatanSidebar --> EnsureSwitchOn["Pastikan switch 'Tampilkan Anomali' AKTIF"]
    EnsureSwitchOn --> WriteGenNote3["Tulis Catatan '#3' pada catatan umum"]
    WriteGenNote3 --> SubmitForm["Kirim & Konfirmasi Formulir"]
```

#### D. Detail Aturan Percabangan:
1. **Pencarian ART**: Bot memeriksa kesesuaian antara nama anggota keluarga (`nama_dtsen`) dan nomor urut di Kartu Keluarga (`no_urut_kk`) pada sub-sidebar.
2. **Koreksi NIK & Remark `#3`**:
   - Jika terdapat NIK baru dari hasil pemadanan dokumen (16 digit): bot mengosongkan input lama dan mengetikkan NIK yang baru.
   - Membuka modal Catatan pada Rincian 30 dan membubuhkan catatan **`#3`**.
   - Membuka sidebar CATATAN, memastikan switch anomali aktif, dan membubuhkan catatan `#3`.

---

### 4.7. 🆔 Modul Cleaning NIK R29 SE2026 (Penanggung Jawab Usaha) (`cleaning_nik_r29`)

#### A. Latar Belakang & Tujuan
Menangani verifikasi dan pembersihan identitas **Penanggung Jawab Usaha pada Rincian 29 (R29)**.

#### B. Kolom Excel yang Dibutuhkan
* `keg_utama` / `nama_usaha`, `nik_target`, `url`, `Status_Eksekusi`, `Keterangan`

#### C. Diagram Alur Logika (Flowchart):
```mermaid
flowchart TD
    Start["Buka URL Penugasan Fasih"] --> OpenR29["Buka Menu: Rincian 29 (Penanggung Jawab Usaha)"]
    OpenR29 --> ReadR29NIK["Baca isian NIK Penanggung Jawab saat ini"]
    ReadR29NIK --> CheckKoreksi{"Apakah ada perbaikan NIK di Excel (16 digit)?"}
    CheckKoreksi -->|Ada Koreksi| FillNewNIK["Timpa field NIK dengan 16 digit yang benar"]
    CheckKoreksi -->|Tidak Ada Koreksi| ValidateFormat["Pastikan format NIK sah"]
    FillNewNIK --> AddRemarkR29["Klik tombol Catatan di Rincian 29 -> Tulis catatan verifikasi"]
    ValidateFormat --> AddRemarkR29
    AddRemarkR29 --> OpenCatatanSidebar["Buka Menu CATATAN di Sidebar"]
    OpenCatatanSidebar --> EnsureSwitchOn["Pastikan switch 'Tampilkan Anomali Usaha dan Keluarga' AKTIF"]
    EnsureSwitchOn --> WriteCatatanR29["Tulis catatan verifikasi penanggung jawab"]
    WriteCatatanR29 --> SubmitForm["Kirim & Konfirmasi Formulir"]
```

#### D. Detail Aturan Percabangan:
1. Memeriksa keberadaan NIK pada formulir R29.
2. Jika ada pembaruan digit NIK, field diperbarui dengan simulasi ketikan manusia.
3. Menyematkan catatan verifikasi identitas pengelola usaha pada field R29 dan menu sidebar CATATAN.

---

### 4.8. 🆔 Modul Cleaning NIK R27 SE2026 (Pemilik Usaha) (`cleaning_nik_r27`)

#### A. Latar Belakang & Tujuan
Menangani konfirmasi NIK **Pemilik Usaha pada Rincian 27 (R27)**. Memastikan NIK pemilik usaha yang sudah benar dibubuhi catatan pengesahan `#0` agar status anomali di portal pusat bersih.

#### B. Kolom Excel yang Dibutuhkan
* `keg_utama` / `nama_usaha`, `url`, `Status_Eksekusi`, `Keterangan`

#### C. Diagram Alur Logika (Flowchart):
```mermaid
flowchart TD
    Start["Buka URL Penugasan Fasih"] --> OpenR27["Buka Rincian 27 (NIK Pemilik Usaha: div#r27)"]
    OpenR27 --> ClickCatatanR27["Klik tombol Catatan pada Rincian 27"]
    ClickCatatanR27 --> CheckExistingNote{"Apakah Catatan '#0' sudah pernah dikirim sebelumnya?"}
    CheckExistingNote -->|Sudah Ada| CloseModal["Tutup modal Catatan (Idempoten: Tanpa Kirim Ulang)"]
    CheckExistingNote -->|Belum Ada| SendNote0["Ketik '#0' -> Klik tombol Simpan -> Tutup modal"]
    CloseModal --> OpenCatatanSidebar["Buka Menu CATATAN di Sidebar"]
    SendNote0 --> OpenCatatanSidebar
    OpenCatatanSidebar --> EnsureSwitchOn["Pastikan switch 'Tampilkan Anomali Usaha dan Keluarga' AKTIF"]
    EnsureSwitchOn --> WriteCatatan0["Tulis Catatan '#0' pada catatan umum"]
    WriteCatatan0 --> CheckGalat{"Apakah ada indikator galat merah?"}
    CheckGalat -->|Ada Galat| AbortSubmit["Batalkan Kirim (Gagal Validasi Formulir)"]
    CheckGalat -->|Tanpa Galat| SubmitForm["Klik Kirim -> Ringkasan Kirim -> Konfirmasi Kirim"]
```

#### D. Detail Aturan Percabangan:
1. **Pemeriksaan Idempoten**: Bot membaca riwayat pesan di modal catatan R27. Jika catatan `#0` sudah pernah dikirim, bot tidak mengirim ulang untuk menghindari banjir riwayat catatan.
2. **Penyelesaian**: Mengaktifkan switch anomali di Blok Catatan, membubuhkan catatan `#0`, dan melakukan submit formulir.

---

### 4.9. ✅ Modul Approve SE2026 (PML / Taskforce) (`approve_se2026`)

#### A. Latar Belakang & Tujuan
Dirancang untuk mempercepat tugas pengawasan bagi **PML (Pengawas)** dan **Tim Taskforce** dalam menyetujui (*approve*) dokumen hasil pencacahan dan data cleaning yang sudah berstatus lengkap secara massal.

#### B. Diagram Alur Logika (Flowchart):
```mermaid
flowchart TD
    Start["Buka Halaman Monitoring Pengawasan Fasih"] --> FilterReady["Filter Penugasan berstatus 'Siap Disetujui'"]
    FilterReady --> OpenAssignment["Buka Dokumen Penugasan Target"]
    OpenAssignment --> CheckIntegrity{"Pemeriksaan Integritas: Apakah ada galat / isian kosong?"}
    CheckIntegrity -->|Ada Galat| FlagReject["Tandai Perlu Revisi Petugas (Reject / Return)"]
    CheckIntegrity -->|Lengkap dan Bersih| ClickApprove["Klik tombol 'Setujui / Approve'"]
    ClickApprove --> ConfirmModal["Konfirmasi dialog pop-up persetujuan"]
    ConfirmModal --> LogReport["Catat status APPROVED & timestamp ke Excel laporan"]
    FlagReject --> LogReport
    LogReport --> NextAssignment["Lanjut ke penugasan berikutnya"]
```

#### C. Detail Tahapan:
1. Membuka daftar antrean dokumen pengawas.
2. Melakukan *smoke check* kelayakan formulir.
3. Menjalankan aksi persetujuan (*Approve*) dan menyimpan log audit.

---

## 🛡️ Fitur Keamanan, Anti-Detection, & Penanganan Sesi SSO

Aplikasi ini dilengkapi arsitektur pertahanan berlapis untuk menjamin kelancaran otomasi ribuan record tanpa terhalang proteksi firewall web server BPS:

1. **Simulasi Interaksi Manusiawi (*Human-Like Typing & Jitter*)**:
   - Seluruh klik tombol, pemilihan radio, dan pengetikan teks dilengkapi penundaan acak mikro (*micro-jitter* antara 0.1s s.d. 0.4s).
   - Menghindari pola request instan yang biasa dideteksi oleh Web Application Firewall (WAF F5 BIG-IP).
2. **Session Guard & Pemulihan Sesi Real-Time**:
   - Bot terus memantau status login SSO BPS pada setiap pergantian baris dan setiap klik tombol.
   - Jika sesi SSO berakhir di tengah jalan: bot **tidak akan crash atau gagal**, melainkan otomatis **menjeda pekerjaan (pause)**, memunculkan jendela browser ke layar depan agar Anda dapat login kembali, lalu melanjutkan baris yang tertunda secara mulus!
3. **Penyimpanan Checkpoint & Auto-Resume**:
   - Status pengerjaan tiap baris (`SUKSES`, `DILEWATI`, atau `GAGAL`) langsung disimpan seketika ke file Excel kerja.
   - Jika aplikasi ditutup atau komputer mati mendadak, Anda cukup memuat kembali file Excel yang sama, dan bot otomatis melewati (*skip*) baris yang sudah bertanda `SUKSES`.
4. **Proteksi File Lock Windows (`WinError 32`)**:
   - Jika file Excel sedang dibuka di aplikasi Microsoft Excel saat bot hendak menyimpan data, bot otomatis membuat salinan cadangan berkala (`_autosave.xlsx`) agar data tidak hilang dan aplikasi tidak berhenti mendadak.

---

## 📦 Panduan Instalasi & Build Installer Windows

### 1. Menjalankan via File Installer (Untuk Pengguna Umum / Non-Teknis)
Anda **tidak memerlukan Python** di komputer Anda. Cukup unduh dan jalankan file installer resmi:
* 📥 [FASIH_3603_Helper_Setup_v1.8.0.exe](file:///d:/3603%20BPS%20Kab%20Tangerang/2026/Sensus%20Ekonomi/Anomali/Fasih%203603%20Helper/desktop_app/dist_installer/FASIH_3603_Helper_Setup_v1.8.0.exe)
* Ikuti petunjuk wizard instalasi. Shortcut aplikasi akan otomatis terpasang di Desktop dan Menu Start Windows.

### 2. Menjalankan di Lingkungan Pengembangan (Developer Mode)
```powershell
# 1. Pindah ke direktori desktop_app
cd "d:\3603 BPS Kab Tangerang\2026\Sensus Ekonomi\Anomali\Fasih 3603 Helper\desktop_app"

# 2. Aktifkan environment Python (Conda)
conda activate automation

# 3. Jalankan aplikasi GUI desktop
python main.py
```

### 3. Kompilasi Ulang File Setup Installer (Build PyInstaller & Inno Setup)
Jika Anda melakukan perubahan kode sumber dan ingin mengemas ulang aplikasi ke installer Windows:
```powershell
cd "d:\3603 BPS Kab Tangerang\2026\Sensus Ekonomi\Anomali\Fasih 3603 Helper\desktop_app"
python build/build_exe.py
```
*Skrip `build_exe.py` akan secara otomatis menjalankan PyInstaller (bundle onedir) dan memanggil Inno Setup Compiler 7 untuk membuat file `.exe` setup baru di dalam folder `dist_installer/`.*

---

## 📞 Bantuan & Dukungan Teknis
Aplikasi ini dikembangkan untuk mendukung kelancaran kegiatan sensus dan survei di **BPS Kabupaten Tangerang**.  
Jika Anda menemukan kendala teknis, anomali baru pada formulir Fasih, atau memerlukan penyesuaian aturan modul, silakan hubungi tim pengembang IT BPS Kabupaten Tangerang.
