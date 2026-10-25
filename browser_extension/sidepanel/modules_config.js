// ==============================================================================
// FASIH 3603 HELPER - CONFIGURATION & EXCEL COLUMN MAPPING PER MODULE
// ==============================================================================

window.MODULES_CONFIG = {
  remark_kbli: {
    id: "remark_kbli",
    name: "Remark KBLI SE2026",
    badge: "🏷️ Remark KBLI",
    description: "Verifikasi KBLI Tetap (#0) atau Ganti (#4), pemilihan Master KBLI, Halal, dan Izin Edar",
    mandatoryKeys: ["assignment_id", "url", "st_kbli"],
    columnAliases: {
      assignment_id: ["assignment_id", "assignment id", "id_assignment", "id", "assignment"],
      url: ["url", "link_fasih_sm", "link", "link fasih", "link_fasih", "tautan"],
      kegiatan_utama: ["kegiatan_utama", "keg_utama", "kegiatan utama", "nama_kegiatan", "nama kegiatan", "uraian"],
      kbli_lama: ["kbli_lama", "kbli lama", "kbli_awal", "kbli awal"],
      st_kbli: ["st_kbli", "status_kbli", "status kbli", "st kbli", "kondisi"],
      kbli_baru: ["kbli_baru", "kbli baru", "kbli_terbaru", "kbli terbaru", "kbli_update", "kbli"],
      status: ["status_eksekusi", "status_proses", "status"],
      keterangan: ["keterangan", "ket", "catatan_eksekusi"]
    },
    sampleData: [
      {
        assignment_id: "3603-KBLI-001",
        url: "https://fasih-sm.bps.go.id/assignment/detail/sample-1",
        kegiatan_utama: "PERDAGANGAN ECERAN BERAS DAN SEMBAKO",
        kbli_lama: "47111",
        st_kbli: "1",
        kbli_baru: "47111",
        status: "",
        keterangan: ""
      },
      {
        assignment_id: "3603-KBLI-002",
        url: "https://fasih-sm.bps.go.id/assignment/detail/sample-2",
        kegiatan_utama: "KEDAI MAKANAN DAN MINUMAN KELILING",
        kbli_lama: "56101",
        st_kbli: "2",
        kbli_baru: "56102",
        status: "",
        keterangan: ""
      }
    ]
  },

  kbli_sembako: {
    id: "kbli_sembako",
    name: "KBLI Sembako SE2026",
    badge: "🛒 KBLI Sembako",
    description: "Penyesuaian KBLI 47111 vs 47211 minimarket / kelontong sembako",
    mandatoryKeys: ["assignment_id", "url", "st_kbli"],
    columnAliases: {
      assignment_id: ["assignment_id", "assignment id", "id_assignment", "id", "assignment"],
      url: ["url", "link_fasih_sm", "link", "link fasih", "link_fasih", "tautan"],
      kegiatan_utama: ["kegiatan_utama", "keg_utama", "kegiatan utama", "nama_kegiatan"],
      st_kbli: ["st_kbli", "status_kbli", "status kbli", "st kbli"],
      kbli_baru: ["kbli_baru", "kbli baru", "kbli_terbaru", "kbli terbaru", "kbli"],
      status: ["status_eksekusi", "status_proses", "status"],
      keterangan: ["keterangan", "ket", "catatan_eksekusi"]
    },
    sampleData: [
      {
        assignment_id: "3603-SMBK-001",
        url: "https://fasih-sm.bps.go.id/assignment/detail/sample-sembako-1",
        kegiatan_utama: "TOKO KELONTONG SEMBAKO",
        st_kbli: "1",
        kbli_baru: "47111",
        status: "",
        keterangan: ""
      }
    ]
  },

  kbli_pmm: {
    id: "kbli_pmm",
    name: "KBLI PMM SE2026",
    badge: "📦 KBLI PMM",
    description: "Penyedia Makanan & Minuman (56101 Restoran vs 56102 Kedai/Keliling), 13.b1, 13.b, 13.c",
    mandatoryKeys: ["assignment_id", "url", "kbli_akhir"],
    columnAliases: {
      assignment_id: ["assignment_id", "assignment id", "id_assignment", "id", "assignment"],
      url: ["url", "link_fasih_sm", "link", "link fasih", "link_fasih", "tautan"],
      kegiatan_utama: ["kegiatan_utama", "keg_utama", "kegiatan utama"],
      kbli_akhir: ["kbli_akhir", "kbli akhir", "kbli_baru", "kbli baru", "kbli"],
      st_kbli: ["st_kbli", "status_kbli", "st kbli"],
      status: ["status_eksekusi", "status_proses", "status"],
      keterangan: ["keterangan", "ket", "catatan_eksekusi"]
    },
    sampleData: [
      {
        assignment_id: "3603-PMM-001",
        url: "https://fasih-sm.bps.go.id/assignment/detail/sample-pmm-1",
        kegiatan_utama: "WARUNG NASI DAN RESTORAN",
        kbli_akhir: "56101",
        st_kbli: "1",
        status: "",
        keterangan: ""
      },
      {
        assignment_id: "3603-PMM-002",
        url: "https://fasih-sm.bps.go.id/assignment/detail/sample-pmm-2",
        kegiatan_utama: "PEDAGANG GORENGAN KELILING",
        kbli_akhir: "56102",
        st_kbli: "2",
        status: "",
        keterangan: ""
      }
    ]
  },

  cleaning_usaha: {
    id: "cleaning_usaha",
    name: "Cleaning Usaha SE2026",
    badge: "🧹 Cleaning Usaha",
    description: "Pembersihan anomali karakteristik usaha, total pengeluaran, pendapatan, dan total aset",
    mandatoryKeys: ["url"],
    columnAliases: {
      assignment_id: ["assignment_id", "assignment id", "id_assignment", "id", "assignment", "no", "id penugasan"],
      url: ["url", "link_fasih_sm", "link", "link fasih", "link_fasih", "tautan"],
      nama_usaha: ["nama_usaha", "nama usaha", "nama perusahaan", "kegiatan_utama", "keg_utama"],
      total_pengeluaran: ["total pengeluaran", "total_pengeluaran"],
      total_pengeluaran_raw: ["total pengeluaran [raw]", "total pengeluaran raw", "total_pengeluaran_raw"],
      total_pendapatan: ["total pendapatan", "total_pendapatan"],
      total_pendapatan_raw: ["total pendapatan [raw]", "total pendapatan raw", "total_pendapatan_raw"],
      total_aset: ["total aset", "total asset", "total_aset"],
      total_aset_raw: ["total aset [raw]", "total aset raw", "total asset [raw]", "total asset raw", "total_aset_raw"],
      upah_dan_gaji: ["upah dan gaji", "upah_dan_gaji", "upah & gaji", "total upah dan gaji", "gaji"],
      biaya_produksi: ["biaya produksi", "biaya_produksi", "produksi"],
      biaya_pembelian_barang_yang_terjual: ["biaya pembelian barang yang terjual", "biaya_pembelian_barang_yang_terjual", "biaya pembelian", "pembelian barang terjual"],
      biaya_operasional: ["biaya operasional", "biaya_operasional", "operasional"],
      biaya_non_operasional: ["biaya non operasional", "biaya_non_operasional", "biaya non-operasional", "non operasional"],
      nilai_pendapatan_barang_dan_jasa: ["nilai pendapatan barang dan jasa", "nilai_pendapatan_barang_dan_jasa", "pendapatan barang dan jasa", "penjualan barang dan jasa"],
      pendapatan_lainnya: ["pendapatan lainnya", "pendapatan_lainnya", "pendapatan lain"],
      status: ["status_eksekusi", "status_proses", "status"],
      keterangan: ["keterangan", "ket", "catatan_eksekusi"]
    },
    sampleData: [
      {
        assignment_id: "3603-USAHA-001",
        url: "https://fasih-sm.bps.go.id/penugasan/detail/sample-usaha-1",
        nama_usaha: "BENGKEL MOTOR MAJU",
        total_pengeluaran: 15000000,
        total_pengeluaran_raw: 12000000,
        total_pendapatan: 25000000,
        total_pendapatan_raw: 25000000,
        total_aset: 50000000,
        total_aset_raw: 40000000,
        upah_dan_gaji: 5000000,
        biaya_produksi: 3000000,
        biaya_operasional: 7000000,
        nilai_pendapatan_barang_dan_jasa: 25000000,
        status: "",
        keterangan: ""
      }
    ]
  },

  cleaning_nik_r30: {
    id: "cleaning_nik_r30",
    name: "Cleaning NIK R30 SE2026",
    badge: "🆔 NIK R30",
    description: "Pembersihan NIK ART berdasarkan nomor urut KK & nama anggota keluarga",
    mandatoryKeys: ["url", "no_urut_kk", "nomor_induk_kependudukan"],
    columnAliases: {
      assignment_id: ["assignment_id", "assignment id", "id_assignment", "id"],
      url: ["url", "link_fasih_sm", "link", "link fasih", "link_fasih", "tautan"],
      no_urut_kk: ["no_urut_kk", "no urut kk", "no_urut", "nourutkk", "no urut", "no_art"],
      nomor_induk_kependudukan: ["nomor_induk_kependudukan", "nik", "no_nik", "no nik"],
      nama: ["nama", "nama_lengkap", "nama lengkap", "nama_art"],
      catatan: ["catatan", "remark", "keterangan_catatan"],
      status: ["status_eksekusi", "status_proses", "status"],
      keterangan: ["keterangan", "ket", "catatan_eksekusi"]
    },
    sampleData: [
      {
        assignment_id: "3603-NIK30-001",
        url: "https://fasih-sm.bps.go.id/penugasan/detail/sample-nik-1",
        no_urut_kk: "1",
        nama: "AHMAD JUNAEDI",
        nomor_induk_kependudukan: "3603010101900001",
        catatan: "#3",
        status: "",
        keterangan: ""
      }
    ]
  },

  cleaning_nik_r27: {
    id: "cleaning_nik_r27",
    name: "Cleaning NIK R27 SE2026",
    badge: "🆔 NIK R27",
    description: "Pemeriksaan dan remarking NIK ART menyeluruh per penugasan keluarga",
    mandatoryKeys: ["url", "total_nik"],
    columnAliases: {
      assignment_id: ["assignment_id", "assignment id", "id_assignment", "id"],
      url: ["url", "link_fasih_sm", "link", "link fasih", "link_fasih", "tautan"],
      total_nik: ["total_nik", "total nik", "total", "jml_nik", "jumlah_nik"],
      nik: ["nik", "no_nik", "nomor_induk_kependudukan"],
      status: ["status_eksekusi", "status_proses", "status"],
      keterangan: ["keterangan", "ket", "catatan_eksekusi", "catatan"]
    },
    sampleData: [
      {
        assignment_id: "3603-NIK27-001",
        url: "https://fasih-sm.bps.go.id/penugasan/detail/sample-nik27-1",
        total_nik: 2,
        nik_1: "3603010101900001",
        nik_2: "3603010101900002",
        status: "",
        keterangan: ""
      }
    ]
  }
};
