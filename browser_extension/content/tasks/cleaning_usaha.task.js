// ==============================================================================
// FASIH 3603 HELPER - TASK: DATA CLEANING USAHA SE2026 (KEUANGAN & ASET)
// Paritas 100% dengan modules/cleaning_usaha/engine.py
// ==============================================================================

(function () {
  const FH = window.FH;

  const SELECTORS = {
    sidebar_container: ".fasih-form-sidebar, div[class*='sidebar']",
    sidebar_blok_ii: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')] | //*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')]",
    sidebar_ket_usaha: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[@title='Keterangan Usaha/Perusahaan' or text()='Keterangan Usaha/Perusahaan']",
    sidebar_blok_catatan: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='CATATAN' or normalize-space(text())='CATATAN' or contains(text(), 'CATATAN')] | //*[@title='CATATAN' or normalize-space(text())='CATATAN']",
    total_pengeluaran: "div[id^='total_pengeluaran#'], div[id='total_pengeluaran']",
    total_pendapatan: "div[id^='total_pendapatan#'], div[id='total_pendapatan']",
    total_aset: "div[id^='total_aset_thn#'], div[id^='total_aset#'], div[id='total_aset']",
    btn_kirim: "button#btn-kirim, button:has-text('Kirim')"
  };

  const PENGELUARAN_MAP = [
    {
      name: "Upah dan Gaji",
      keys: ["upah dan gaji", "upah_dan_gaji", "upah & gaji", "total upah dan gaji", "gaji"],
      selector: "div[id^='gaji#']",
      fallback: "xpath=//div[contains(., 'Total upah dan gaji') and .//input[@type='text']]"
    },
    {
      name: "Biaya Produksi",
      keys: ["biaya produksi", "biaya_produksi", "produksi"],
      selector: "div[id^='biaya_produksi#']",
      fallback: "xpath=//div[contains(., 'Biaya produksi') and .//input[@type='text']]"
    },
    {
      name: "Biaya Pembelian Barang yang Terjual",
      keys: ["biaya pembelian barang yang terjual", "biaya_pembelian_barang_yang_terjual", "biaya pembelian", "pembelian barang terjual"],
      selector: "div[id^='biaya_pembelian#']",
      fallback: "xpath=//div[contains(., 'Biaya pembelian barang yang terjual') and .//input[@type='text']]"
    },
    {
      name: "Biaya Operasional",
      keys: ["biaya operasional", "biaya_operasional", "operasional"],
      selector: "div[id^='operasional#']",
      fallback: "xpath=//div[contains(., 'Biaya operasional') and .//input[@type='text']]"
    },
    {
      name: "Biaya Non Operasional",
      keys: ["biaya non operasional", "biaya_non_operasional", "biaya non-operasional", "non operasional"],
      selector: "div[id^='non_operasional#']",
      fallback: "xpath=//div[contains(., 'Biaya non-operasional') and .//input[@type='text']]"
    }
  ];

  const PENDAPATAN_MAP = [
    {
      name: "Nilai Pendapatan Barang dan Jasa",
      keys: ["nilai pendapatan barang dan jasa", "nilai_pendapatan_barang_dan_jasa", "pendapatan barang dan jasa", "penjualan barang dan jasa"],
      selector: "div[id^='nilai_pendapatan#']",
      fallback: "xpath=//div[contains(., 'Nilai penjualan barang dan jasa') and .//input[@type='text']]"
    },
    {
      name: "Pendapatan Lainnya",
      keys: ["pendapatan lainnya", "pendapatan_lainnya", "pendapatan lain"],
      selector: "div[id^='pendapatan_lain#']",
      fallback: "xpath=//div[contains(., 'Pendapatan lainnya yang dihasilkan') and .//input[@type='text']]"
    }
  ];

  const ASET_MAP = {
    tanah_bangunan: {
      name: "Aset Tanah dan Bangunan",
      selector: "div[id^='aset_usaha_thn#'], div[id^='aset_tanah#']",
      fallback: "xpath=//div[contains(., 'aset tanah dan bangunan') and .//input[@type='text']]"
    },
    selain_tanah: {
      name: "Aset Selain Tanah dan Bangunan",
      selector: "div[id^='aset_lain_thn#'], div[id^='aset_lain#'], div[id^='aset_selain_tanah#']",
      fallback: "xpath=//div[contains(., 'aset selain tanah dan bangunan') and .//input[@type='text']]"
    },
    total_aset: {
      name: "Total Aset (Field Remarks)",
      selector: "div[id^='total_aset_thn#'], div[id^='total_aset#'], div[id='total_aset']",
      fallback: "xpath=//div[contains(., 'Nilai total aset') and .//button[contains(@title, 'Catatan')]]"
    }
  };

  function isValuesDifferent(valClean, valRaw) {
    const cleanEmpty = valClean === undefined || valClean === null || String(valClean).trim() === "";
    const rawEmpty = valRaw === undefined || valRaw === null || String(valRaw).trim() === "";
    if (cleanEmpty && rawEmpty) return false;
    if (cleanEmpty !== rawEmpty) return true;

    const cleanNum = Number(valClean);
    const rawNum = Number(valRaw);
    if (!isNaN(cleanNum) && !isNaN(rawNum)) {
      return Math.round(cleanNum) !== Math.round(rawNum);
    }
    return String(valClean).trim() !== String(valRaw).trim();
  }

  function getRowValue(row, keys) {
    for (const k of keys) {
      if (row[k] !== undefined && row[k] !== null && String(row[k]).trim() !== "") return row[k];
      if (row._raw && row._raw[k] !== undefined && row._raw[k] !== null && String(row._raw[k]).trim() !== "") return row._raw[k];
    }
    return null;
  }

  // STEP 2: Buka Sub Sidebar Blok II / Nama Usaha (Persis sama dengan Python)
  async function openMatchingUsaha(targetName) {
    FH.log("info", "Menunggu elemen sidebar formulir Fasih...");
    await FH.waitFor(SELECTORS.sidebar_container, { timeout: 35000, state: "attached" });

    FH.log("info", "Membuka menu 'SE2026 - L BLOK II' di sidebar...");
    const blok2 = await FH.waitFor(SELECTORS.sidebar_blok_ii, { timeout: 35000 });
    await FH.humanClick(blok2);
    await FH.randomSleep(0.8, 1.4);

    // Cek apakah ada sub-header 'Keterangan Usaha/Perusahaan' yang perlu di-expand
    const menuUsaha = FH.find(SELECTORS.sidebar_ket_usaha);
    if (menuUsaha && FH.isVisible(menuUsaha)) {
      const parent = menuUsaha.parentElement;
      const isExpanded = parent && (parent.getAttribute("data-expanded") === "true" || parent.querySelector("div[data-expanded='true']"));
      if (!isExpanded) {
        FH.log("info", "Membuka sub-menu 'Keterangan Usaha/Perusahaan'...");
        await FH.humanClick(menuUsaha);
        await FH.randomSleep(0.6, 1.0);
      }
    }

    // Cari item usaha di sub-sidebar
    const cleanTarget = (targetName || "").toLowerCase().trim();
    let usahaItem = null;

    if (cleanTarget) {
      FH.log("info", `Mencari item usaha '${targetName}' di sub-sidebar...`);
      // Cari elemen cursor-pointer yang mengandung nama usaha
      const allSub = FH.findAll("xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[contains(@class, 'cursor-pointer')] | //div[contains(@class, 'cursor-pointer')]");
      for (const el of allSub) {
        const text = (el.textContent || "").toLowerCase();
        const title = (el.getAttribute("title") || "").toLowerCase();
        if (text.includes(cleanTarget) || title.includes(cleanTarget)) {
          usahaItem = el;
          FH.log("info", `Ditemukan item usaha cocok: '${el.getAttribute("title") || el.textContent.trim().slice(0, 30)}'`);
          break;
        }
      }
    }

    // Jika tidak ditemukan berdasarkan nama, ambil item sub pertama di Blok II
    if (!usahaItem) {
      FH.log("info", "Mencari item usaha pertama di Blok II...");
      const rawCandidates = FH.findAll("xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[contains(@class, 'cursor-pointer') and not(contains(., 'BLOK II')) and not(contains(., 'CATATAN'))] | //div[contains(@class, 'cursor-pointer') and not(contains(., 'BLOK II')) and not(contains(., 'CATATAN'))]");
      for (const el of rawCandidates) {
        const title = (el.getAttribute("title") || el.textContent || "").toUpperCase();
        if (title && !title.includes("BLOK II") && !title.includes("CATATAN") && !title.includes("KETERANGAN USAHA")) {
          usahaItem = el;
          FH.log("info", `Menggunakan item usaha pertama: '${el.getAttribute("title") || el.textContent.trim().slice(0, 30)}'`);
          break;
        }
      }
    }

    if (usahaItem) {
      await FH.humanClick(usahaItem);
      await FH.randomSleep(1.5, 2.5);
    } else {
      FH.log("warn", "Sub-item usaha tidak ditemukan, melanjutkan dengan form yang sedang aktif...");
    }

    // Tunggu form utama tampil (Total Pengeluaran)
    FH.log("info", "Menunggu elemen rincian usaha ('total_pengeluaran') tampil di formulir...");
    await FH.waitFor(SELECTORS.total_pengeluaran, { timeout: 40000, state: "attached" });
  }

  // Isi Komponen saat Total Berbeda (#4)
  async function fillComponents(compList, row) {
    for (const comp of compList) {
      const val = getRowValue(row, comp.keys);
      // Jika sel komponen kosong / null / undefined -> biarkan saja (skip)
      if (val === null || val === undefined || String(val).trim() === "") {
        continue;
      }

      const num = Number(val);
      if (isNaN(num)) continue;

      const targetVal = Math.round(num);
      let elem = FH.find(comp.selector);
      if (!elem && comp.fallback) {
        elem = FH.find(comp.fallback);
      }

      const isPresent = elem && FH.isVisible(elem);

      if (targetVal === 0) {
        // Jika isiannya 0: cek dulu komponen penyusun di eform fasih elemennya ada atau ngga
        // Jika ada -> timpa dengan 0
        // Jika tidak ada -> biarkan / lewati
        if (isPresent) {
          FH.log("info", `Mengisi ${comp.name}: Rp 0 (menimpa dengan 0)`);
          await FH.safeFillCurrency(elem, 0);
          await FH.randomSleep(0.3, 0.6);
        } else {
          FH.log("info", `Komponen '${comp.name}' bernilai 0 di Excel dan tidak ditemukan di form Fasih -> Dilewati.`);
        }
      } else if (targetVal > 0) {
        if (!isPresent) {
          throw new Error(`Field '${comp.name}' tidak ditemukan di form Fasih, padahal nilai Excel = Rp ${targetVal.toLocaleString("id-ID")}.`);
        }
        FH.log("info", `Mengisi ${comp.name}: Rp ${targetVal.toLocaleString("id-ID")}`);
        await FH.safeFillCurrency(elem, targetVal);
        await FH.randomSleep(0.3, 0.6);
      }
    }
  }

  function readContainerCurrencyValue(selectorOrEl) {
    try {
      const el = typeof selectorOrEl === "string" ? FH.find(selectorOrEl) : selectorOrEl;
      if (!el) return null;
      const inp = el.querySelector("input[type='text'], input");
      if (inp && inp.value && String(inp.value).trim() !== "") {
        return FH.parseFasihCurrency(inp.value);
      }
      const txt = el.textContent || "";
      return FH.parseFasihCurrency(txt);
    } catch (e) {
      return null;
    }
  }

  async function verifyEformTotal(selectorOrEl, targetClean, fieldName, maxWaitSec = 3.5) {
    const targetNum = targetClean !== null && targetClean !== undefined && String(targetClean).trim() !== ""
      ? Math.round(Number(targetClean) || 0)
      : 0;

    const startTime = Date.now();
    let lastVal = null;

    while ((Date.now() - startTime) < maxWaitSec * 1000) {
      lastVal = readContainerCurrencyValue(selectorOrEl);
      if (lastVal !== null && lastVal === targetNum) {
        FH.log("info", `Verifikasi ${fieldName} COCOK: eform Rp ${lastVal.toLocaleString("id-ID")} == Excel Rp ${targetNum.toLocaleString("id-ID")}`);
        return true;
      }
      await FH.sleep(300);
    }

    if (lastVal !== null && lastVal !== targetNum) {
      const diff = Math.abs(lastVal - targetNum);
      const errMsg = `Validasi ${fieldName} TIDAK COCOK setelah pengisian komponen! Total di eform Fasih = Rp ${lastVal.toLocaleString("id-ID")}, sedangkan target di Excel (Clean) = Rp ${targetNum.toLocaleString("id-ID")} (Selisih: Rp ${diff.toLocaleString("id-ID")}). Submit dibatalkan agar data tidak inkonsisten.`;
      FH.log("error", errMsg);
      throw new Error(errMsg);
    }
    return true;
  }

  // STEP 6-8: Submit Flow Berantai (Blok Catatan -> Switch Anomali -> Kirim -> Cek Galat -> Konfirmasi -> Sukses)
  async function submitCleaningUsaha(debugReview) {
    // 1. Buka Blok Catatan
    FH.log("info", "Membuka menu Blok Catatan di sidebar...");
    const menuCatatan = await FH.waitFor(SELECTORS.sidebar_blok_catatan, { timeout: 35000 });
    await FH.humanClick(menuCatatan);
    await FH.randomSleep(1.2, 2.0);

    // 2. Pastikan switch toggle anomali aktif
    await FH.ensureAnomaliSwitchActive(35000);
    await FH.randomSleep(1.8, 2.5);

    if (debugReview) {
      FH.log("info", "[Review Mode] Menghentikan otomatis sebelum submit untuk pemeriksaan manual.");
      return "REVIEW_READY";
    }

    // 3. Klik Kirim pada formulir Fasih (Langkah 1/4)
    FH.log("info", "[1/4] Mengklik tombol Kirim formulir Fasih...");
    const btnKirim = await FH.waitFor(SELECTORS.btn_kirim, { timeout: 25000 });
    await FH.humanClick(btnKirim, { force: true });
    await FH.randomSleep(1.0, 1.8);

    // 4. Pop-up validasi Kirim & hitung Galat (Langkah 2/4)
    FH.log("info", "[2/4] Menunggu pop-up validasi Kirim...");
    const dialogValidasi = await FH.waitFor("div[role='dialog'], div[role='alertdialog'], div:has(button:has-text('Kirim'))", { timeout: 25000 });
    await FH.randomSleep(0.5, 0.8);

    let galatCount = 0;
    try {
      const galatBtn = FH.find("button:has-text('Galat')", dialogValidasi);
      if (galatBtn && FH.isVisible(galatBtn)) {
        const text = galatBtn.textContent || "";
        const m = text.match(/\b(\d+)\b/);
        if (m) galatCount = parseInt(m[1], 10);
      }
    } catch (e) {}

    if (galatCount > 0) {
      FH.pressKey(document.body, "Escape", "Escape");
      throw new Error(`Terdapat ${galatCount} Galat yang perlu diperbaiki. Submit dibatalkan.`);
    }

    // Klik Kirim di dialog validasi
    const btnKirimDialog = FH.find("button:has-text('Kirim')", dialogValidasi);
    if (btnKirimDialog && FH.isVisible(btnKirimDialog)) {
      await FH.humanClick(btnKirimDialog);
      await FH.randomSleep(1.2, 1.8);
    }

    // 5. Konfirmasi Kirim ("Apakah Anda yakin...") (Langkah 3/4)
    FH.log("info", "[3/4] Mengklik Konfirmasi Kirim...");
    const btnKonfirmasi = await FH.waitFor(() => {
      return (
        FH.find("div:has-text('Konfirmasi Kirim') button:has-text('Konfirmasi')") ||
        FH.find("div:has-text('Apakah Anda yakin') button:has-text('Konfirmasi')") ||
        FH.find("button:has-text('Konfirmasi')") ||
        FH.find("div[role='dialog'] button:has-text('Ya')") ||
        FH.byText("button", "Konfirmasi")
      );
    }, { timeout: 20000 });

    if (btnKonfirmasi) {
      await FH.humanClick(btnKonfirmasi);
      await FH.randomSleep(1.5, 2.2);
    }

    // 6. Tunggu dialog sukses (Langkah 4/4)
    FH.log("info", "[4/4] Menunggu konfirmasi respon sukses dari Fasih...");
    await FH.waitFor(() => {
      const txt = document.body.innerText;
      return txt.includes("Berhasil Disubmit") || txt.includes("berhasil disimpan") || txt.includes("Sukses");
    }, { timeout: 25000 });

    FH.log("info", "Formulir penugasan berhasil disubmit dengan sukses.");
    return "SUBMITTED";
  }

  // Task Runner Utama Cleaning Usaha
  FH.tasks.cleaning_usaha = async function (row, options = {}) {
    const { debugReview = false } = options;
    FH.log("info", `[Cleaning Usaha] Memulai baris: Assignment '${row.assignment_id || "-"}' - Usaha: '${row.nama_usaha || "-"}'...`);

    // STEP 2: Buka Sub Sidebar Blok II / Nama Usaha
    const usahaName = row.nama_usaha || row.kegiatan_utama || row.keg_utama || "";
    await openMatchingUsaha(usahaName);

    // STEP 3: Total Pengeluaran
    const tpClean = getRowValue(row, ["total_pengeluaran", "total pengeluaran"]);
    const tpRaw = getRowValue(row, ["total_pengeluaran_raw", "total pengeluaran [raw]", "total pengeluaran raw"]);
    const diffPengeluaran = isValuesDifferent(tpClean, tpRaw);

    let remarksPengeluaran = "#0";
    if (diffPengeluaran) {
      FH.log("info", `Total Pengeluaran BERBEDA (Clean: ${tpClean} vs RAW: ${tpRaw}) -> Mengisi komponen...`);
      await fillComponents(PENGELUARAN_MAP, row);
      await FH.randomSleep(0.5, 0.8);
      await verifyEformTotal(SELECTORS.total_pengeluaran, tpClean, "Total Pengeluaran");
      remarksPengeluaran = "#4";
    } else {
      FH.log("info", `Total Pengeluaran SAMA (Clean: ${tpClean} vs RAW: ${tpRaw}) -> Lewati komponen.`);
      remarksPengeluaran = "#0";
    }

    FH.log("info", `Memberikan remarks '${remarksPengeluaran}' pada Total Pengeluaran...`);
    await FH.addRemark(SELECTORS.total_pengeluaran, remarksPengeluaran);
    await FH.randomSleep(0.5, 0.8);

    // STEP 4: Total Pendapatan
    const tpendClean = getRowValue(row, ["total_pendapatan", "total pendapatan"]);
    const tpendRaw = getRowValue(row, ["total_pendapatan_raw", "total pendapatan [raw]", "total pendapatan raw"]);
    const diffPendapatan = isValuesDifferent(tpendClean, tpendRaw);

    let remarksPendapatan = "#0";
    if (diffPendapatan) {
      FH.log("info", `Total Pendapatan BERBEDA (Clean: ${tpendClean} vs RAW: ${tpendRaw}) -> Mengisi komponen...`);
      await fillComponents(PENDAPATAN_MAP, row);
      await FH.randomSleep(0.5, 0.8);
      await verifyEformTotal(SELECTORS.total_pendapatan, tpendClean, "Total Pendapatan");
      remarksPendapatan = "#4";
    } else {
      FH.log("info", `Total Pendapatan SAMA (Clean: ${tpendClean} vs RAW: ${tpendRaw}) -> Lewati komponen.`);
      remarksPendapatan = "#0";
    }

    FH.log("info", `Memberikan remarks '${remarksPendapatan}' pada Total Pendapatan...`);
    await FH.addRemark(SELECTORS.total_pendapatan, remarksPendapatan);
    await FH.randomSleep(0.5, 0.8);

    // STEP 5: Total Aset
    const taClean = getRowValue(row, ["total_aset", "total aset", "total asset"]);
    const taRaw = getRowValue(row, ["total_aset_raw", "total aset [raw]", "total aset raw", "total asset [raw]"]);
    const diffAset = isValuesDifferent(taClean, taRaw);

    let remarksAset = "#0";
    if (diffAset) {
      const totAsetNum = Math.round(Number(taClean) || 0);
      FH.log("info", `Total Aset BERBEDA (Clean: ${taClean} vs RAW: ${taRaw}) -> Menghitung target Aset (${totAsetNum.toLocaleString("id-ID")})...`);

      const elemTanah = FH.find(ASET_MAP.tanah_bangunan.selector) || FH.find(ASET_MAP.tanah_bangunan.fallback);
      const elemSelainTanah = FH.find(ASET_MAP.selain_tanah.selector) || FH.find(ASET_MAP.selain_tanah.fallback);

      let valExistTanah = 0;
      let valExistLain = 0;
      if (elemTanah) {
        const inp = elemTanah.querySelector("input");
        if (inp) valExistTanah = FH.parseFasihCurrency(inp.value);
      }
      if (elemSelainTanah) {
        const inp = elemSelainTanah.querySelector("input");
        if (inp) valExistLain = FH.parseFasihCurrency(inp.value);
      }

      const totalExist = valExistTanah + valExistLain;
      let asetTanahBaru = 0;
      let asetNonTanahBaru = 0;
      if (totalExist > 0) {
        const propTanah = valExistTanah / totalExist;
        asetTanahBaru = Math.round(totAsetNum * propTanah);
        asetNonTanahBaru = totAsetNum - asetTanahBaru;
      } else {
        const pctTanah = 65; // ~60-70% default tanah
        asetTanahBaru = Math.round(totAsetNum * (pctTanah / 100.0));
        asetNonTanahBaru = totAsetNum - asetTanahBaru;
      }

      if (elemTanah && FH.isVisible(elemTanah)) {
        await FH.safeFillCurrency(elemTanah, asetTanahBaru);
        await FH.randomSleep(0.3, 0.6);
      }
      if (elemSelainTanah && FH.isVisible(elemSelainTanah)) {
        await FH.safeFillCurrency(elemSelainTanah, asetNonTanahBaru);
        await FH.randomSleep(0.3, 0.6);
      }

      await FH.randomSleep(0.5, 0.8);
      await verifyEformTotal(SELECTORS.total_aset, taClean, "Total Aset");
      remarksAset = "#4";
    } else {
      FH.log("info", `Total Aset SAMA (Clean: ${taClean} vs RAW: ${taRaw}) -> Lewati perhitungan aset.`);
      remarksAset = "#0";
    }

    FH.log("info", `Memberikan remarks '${remarksAset}' pada Total Aset...`);
    await FH.addRemark(SELECTORS.total_aset, remarksAset);
    await FH.randomSleep(0.5, 0.8);

    // STEP 6-8: Submit Flow
    const submitResult = await submitCleaningUsaha(debugReview);

    return {
      success: true,
      status: "SELESAI",
      keterangan: submitResult === "REVIEW_READY" ? "Siap Ditinjau (Review Mode)" : `Pembersihan Usaha Sukses (P:${remarksPengeluaran}, Pend:${remarksPendapatan}, Aset:${remarksAset})`
    };
  };
})();
