// ==============================================================================
// FASIH 3603 HELPER - TASK: DC USAHA #3603
// Paritas 100% dengan modules/dc_usaha_#3603/engine.py
// ==============================================================================

(function () {
  const FH = window.FH;

  const SELECTORS = {
    sidebar_container: ".fasih-form-sidebar, div[class*='sidebar']",
    sidebar_blok_ii: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')] | //*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')]",
    sidebar_ket_usaha: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[@title='Keterangan Usaha/Perusahaan' or text()='Keterangan Usaha/Perusahaan']",
    sidebar_blok_catatan: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='CATATAN' or normalize-space(text())='CATATAN' or contains(text(), 'CATATAN')] | //*[@title='CATATAN' or normalize-space(text())='CATATAN']",

    // Selector Total Pengeluaran
    total_pengeluaran: "div[id^='total_pengeluaran#'], div[id='total_pengeluaran']",
    total_pengeluaran_bln: "div[id^='total_pengeluaran_bln#'], div[id='total_pengeluaran_bln']",

    // Selector Total Pendapatan
    total_pendapatan: "div[id^='total_pendapatan#'], div[id='total_pendapatan']",
    total_pendapatan_bln: "div[id^='total_pendapatan_bln#'], div[id='total_pendapatan_bln']",

    btn_kirim: "button#btn-kirim, button:has-text('Kirim')"
  };

  // Helper pencarian container total pengeluaran / pendapatan (tahunan vs _bln 2026)
  async function findTotalContainer(fieldType) {
    const isPengeluaran = fieldType === "pengeluaran";
    const thnSel = isPengeluaran ? SELECTORS.total_pengeluaran : SELECTORS.total_pendapatan;
    const blnSel = isPengeluaran ? SELECTORS.total_pengeluaran_bln : SELECTORS.total_pendapatan_bln;
    const label = isPengeluaran ? "Total Pengeluaran" : "Total Pendapatan";

    let elThn = FH.find(thnSel);
    if (elThn && FH.isVisible(elThn)) {
      return { element: elThn, mode: "TAHUNAN" };
    }

    let elBln = FH.find(blnSel);
    if (elBln && FH.isVisible(elBln)) {
      FH.log("info", `${label} tahunan tidak terdeteksi. Terdeteksi selector _bln (Usaha baru buka 2026): ${blnSel}`);
      return { element: elBln, mode: "BULANAN_2026" };
    }

    return { element: null, mode: null };
  }

  // Helper pengecekan riwayat catatan (apapun isinya)
  async function checkHasExistingRemark(container, fieldName) {
    if (!container) return { hasRemark: false, text: "" };
    try {
      container.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (e) {}
    await FH.randomSleep(0.3, 0.6);

    let btnCatatan = container.querySelector("button[title='Catatan'], button[aria-label='Catatan']");
    if (!btnCatatan || !FH.isVisible(btnCatatan)) {
      const allBtns = container.querySelectorAll("button[title='Catatan'], button[aria-label='Catatan'], button");
      for (const b of allBtns) {
        const titleOrTxt = (b.getAttribute("title") || b.getAttribute("aria-label") || b.textContent || "").toLowerCase();
        if (titleOrTxt.includes("catatan") && FH.isVisible(b)) {
          btnCatatan = b;
          break;
        }
      }
    }

    if (!btnCatatan) {
      throw new Error(`Tombol Catatan visible tidak ditemukan pada ${fieldName}`);
    }

    await FH.humanClick(btnCatatan);
    await FH.randomSleep(0.7, 1.1);

    const dialog = await FH.waitFor("div[role='dialog']", { timeout: 25000 });
    const existingNotes = [];
    const bubbles = dialog.querySelectorAll("div[class*='whitespace-pre-wrap'], div[class*='wrap-break-word'], div[class*='break-words']");
    for (const b of bubbles) {
      const t = b.textContent ? b.textContent.trim() : "";
      if (t) existingNotes.push(t);
    }

    // Tutup dialog
    try {
      const btnClose = dialog.querySelector("button[aria-label='Dismiss'], button[title='Tutup'], button:has-text('Tutup')");
      if (btnClose && FH.isVisible(btnClose)) {
        await FH.humanClick(btnClose);
      } else {
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", code: "Escape", bubbles: true }));
      }
    } catch (e) {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", code: "Escape", bubbles: true }));
    }
    await FH.randomSleep(0.4, 0.7);

    if (existingNotes.length > 0) {
      return { hasRemark: true, text: existingNotes.join(" | ") };
    }
    return { hasRemark: false, text: "" };
  }

  // Buka Sub Sidebar Blok II / Nama Usaha
  async function openMatchingUsaha(usahaName) {
    await FH.waitFor(SELECTORS.sidebar_container, { timeout: 35000 });

    const btnBlokII = await FH.waitFor(SELECTORS.sidebar_blok_ii, { timeout: 30000 });
    await FH.humanClick(btnBlokII);
    await FH.randomSleep(1.0, 1.8);

    if (usahaName) {
      const usahaClean = String(usahaName).trim().toUpperCase();
      const sidebarItems = FH.findAll("div[class*='fasih-form-sidebar'] div[class*='cursor-pointer'], div[class*='cursor-pointer']");
      let matchedItem = null;

      for (const item of sidebarItems) {
        const text = (item.textContent || "").trim().toUpperCase();
        if (text.includes(usahaClean) && !text.includes("BLOK II") && !text.includes("CATATAN")) {
          matchedItem = item;
          break;
        }
      }

      if (matchedItem) {
        FH.log("info", `Memilih usaha di sidebar: '${usahaName}'`);
        await FH.humanClick(matchedItem);
        await FH.randomSleep(1.5, 2.5);
        return;
      }
    }

    const firstSub = FH.find("xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[contains(@class, 'cursor-pointer') and not(contains(., 'BLOK II')) and not(contains(., 'CATATAN'))] | //div[contains(@class, 'cursor-pointer') and not(contains(., 'BLOK II')) and not(contains(., 'CATATAN'))]");
    if (firstSub) {
      await FH.humanClick(firstSub);
      await FH.randomSleep(1.5, 2.5);
    }
  }

  // Submit Flow Berantai (4 Langkah)
  async function submitCleaningUsaha(debugReview = false) {
    // 1. Menuju Blok Catatan di Sidebar
    FH.log("info", "Membuka Blok Catatan di Sidebar...");
    const btnCatatan = await FH.waitFor(SELECTORS.sidebar_blok_catatan, { timeout: 35000 });
    await FH.humanClick(btnCatatan);
    await FH.randomSleep(1.2, 2.0);

    // 2. Switch Anomali
    await FH.ensureAnomaliSwitchActive(35000);
    await FH.randomSleep(1.5, 2.2);

    // 3. Klik Kirim pada formulir (Langkah 1/4)
    FH.log("info", "[1/4] Mengklik tombol Kirim formulir Fasih...");
    const btnKirimForm = await FH.waitFor("button#btn-kirim, button:has-text('Kirim')", { timeout: 25000 });
    await FH.humanClick(btnKirimForm);
    await FH.randomSleep(1.2, 1.8);

    // 4. Pop-up validasi Kirim (Langkah 2/4)
    const dialogValidasi = await FH.waitFor("div[role='dialog'], div[role='alertdialog']", { timeout: 25000 });

    let galatCount = 0;
    try {
      const galatCard = FH.find("button:has-text('Galat')", dialogValidasi);
      if (galatCard && FH.isVisible(galatCard)) {
        const text = galatCard.textContent || "";
        const lines = text.split("\n").map(l => l.trim()).filter(Boolean);
        for (const line of lines) {
          if (!isNaN(line) && line.length > 0) {
            galatCount = parseInt(line, 10);
            break;
          }
        }
      }
    } catch (e) {}

    if (galatCount > 0) {
      const errMsg = `Terdapat ${galatCount} Galat yang perlu diperbaiki. Submit dibatalkan.`;
      FH.log("warn", errMsg);
      const btnBatal = FH.find("button:has-text('Batal')", dialogValidasi);
      if (btnBatal) await FH.humanClick(btnBatal);
      throw new Error(errMsg);
    }

    FH.log("info", "[2/4] Galat = 0. Melanjutkan submit...");
    if (debugReview) {
      FH.log("warn", "Mode Review aktif. Pengiriman dijeda untuk peninjauan manual.");
      return "REVIEW_READY";
    }

    const btnKirimDialog = FH.find("button:has-text('Kirim')", dialogValidasi);
    if (btnKirimDialog && FH.isVisible(btnKirimDialog)) {
      await FH.humanClick(btnKirimDialog);
      await FH.randomSleep(1.2, 1.8);
    }

    // 5. Konfirmasi Kirim (Langkah 3/4)
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
    FH.log("info", "[4/4] Menunggu konfirmasi sukses submit dari server...");
    await FH.waitFor(() => {
      return (
        FH.find("div[role='alertdialog']:has-text('Assignment Berhasil Disubmit')") ||
        FH.find("h2:has-text('Assignment Berhasil Disubmit')") ||
        FH.find("p:has-text('Perubahan Anda berhasil disimpan')") ||
        FH.byText("div", "Assignment Berhasil Disubmit")
      );
    }, { timeout: 25000 });

    FH.log("info", "Formulir penugasan berhasil disubmit dengan sukses.");
    return "SUBMITTED";
  }

  // Task Runner Utama DC Usaha #3603
  FH.tasks.dc_usaha_3603 = async function (row, options = {}) {
    const { debugReview = false } = options;
    FH.log("info", `[DC Usaha #3603] Memulai baris: Assignment '${row.assignment_id || "-"}' - Usaha: '${row.nama_usaha || "-"}'...`);

    // STEP 1 & 2: Buka Sub Sidebar Blok II / Nama Usaha jika ada
    const usahaName = row.nama_usaha || row.kegiatan_utama || row.keg_utama || "";
    await openMatchingUsaha(usahaName);

    // STEP 3: Deteksi Container Total Pengeluaran & Total Pendapatan
    const contPengeluaran = await findTotalContainer("pengeluaran");
    if (!contPengeluaran.element) {
      throw new Error("Rincian Total Pengeluaran (tahunan maupun bulanan) tidak ditemukan pada formulir.");
    }

    const contPendapatan = await findTotalContainer("pendapatan");
    if (!contPendapatan.element) {
      throw new Error("Rincian Total Pendapatan (tahunan maupun bulanan) tidak ditemukan pada formulir.");
    }

    FH.log("info", `Rincian terdeteksi: Total Pengeluaran [${contPengeluaran.mode}], Total Pendapatan [${contPendapatan.mode}].`);

    // STEP 4: Cek Catatan Sebelumnya (SKIP jika sudah ada remark, status SUKSES)
    FH.log("info", "Memeriksa riwayat catatan pada Total Pengeluaran...");
    const checkP = await checkHasExistingRemark(contPengeluaran.element, "Total Pengeluaran");
    if (checkP.hasRemark) {
      const skipMsg = `Sudah ada catatan pada Total Pengeluaran ('${checkP.text}'). Dilewati.`;
      FH.log("info", `[SUKSES] ${skipMsg} Melewati assignment sesuai aturan.`);
      return {
        success: true,
        status: "SUKSES",
        keterangan: skipMsg
      };
    }

    FH.log("info", "Memeriksa riwayat catatan pada Total Pendapatan...");
    const checkPend = await checkHasExistingRemark(contPendapatan.element, "Total Pendapatan");
    if (checkPend.hasRemark) {
      const skipMsg = `Sudah ada catatan pada Total Pendapatan ('${checkPend.text}'). Dilewati.`;
      FH.log("info", `[SUKSES] ${skipMsg} Melewati assignment sesuai aturan.`);
      return {
        success: true,
        status: "SUKSES",
        keterangan: skipMsg
      };
    }

    // STEP 5: Memberikan Catatan Remark
    // 1. Total Pengeluaran = #0
    FH.log("info", `Memberikan catatan '#0' pada Total Pengeluaran (${contPengeluaran.mode})...`);
    await FH.addRemark(contPengeluaran.element, "#0");
    await FH.randomSleep(0.5, 0.8);

    // 2. Total Pendapatan = #3603
    FH.log("info", `Memberikan catatan '#3603' pada Total Pendapatan (${contPendapatan.mode})...`);
    await FH.addRemark(contPendapatan.element, "#3603");
    await FH.randomSleep(0.5, 0.8);

    // STEP 6: Submit Flow (Tanpa menyentuh Aset)
    const submitResult = await submitCleaningUsaha(debugReview);

    return {
      success: true,
      status: "SELESAI",
      keterangan: submitResult === "REVIEW_READY" ? "Siap Ditinjau (Review Mode)" : `Pembersihan Usaha Sukses (P:#0 [${contPengeluaran.mode}], Pend:#3603 [${contPendapatan.mode}])`
    };
  };
})();
