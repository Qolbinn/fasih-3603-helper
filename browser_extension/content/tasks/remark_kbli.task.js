// ==============================================================================
// FASIH 3603 HELPER - TASK: REMARK KBLI SE2026
// Paritas 100% dengan modules/remark_kbli/engine.py
// ==============================================================================

(function () {
  const FH = window.FH;

  const SELECTORS = {
    sidebar_container: ".fasih-form-sidebar, div[class*='sidebar']",
    sidebar_blok_ii: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')] | //*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')]",
    sidebar_ket_usaha: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[@title='Keterangan Usaha/Perusahaan' or text()='Keterangan Usaha/Perusahaan']",
    container_keg_utama: "div[id^='keg_utama#'], div[id='keg_utama'], div[id^='kegiatan_utama#'], div[id='kegiatan_utama']",
    field_kegiatan_utama: "div[id^='keg_utama#'] input[type='text'], div[id^='keg_utama#'] textarea, div[id*='keg_utama'] input, div[id^='kegiatan_utama#'] textarea, div[id^='kegiatan_utama#'] input, textarea#kegiatan_utama, input#kegiatan_utama",
    container_kbli_genai: "div[id^='kbli_genai#'], div[id='kbli_genai']",
    container_master_kbli: "div[id^='kbli#'], div[id='kbli']",
    textarea_master_kbli: "input[type='text'], textarea",
    container_halal: "div[id^='halal#'], div[id='halal']",
    container_izin_edar: "div[id^='izin_edar#'], div[id='izin_edar']",
    btn_kirim: "button#btn-kirim, button:has-text('Kirim')"
  };

  async function cleanKbliCode(val) {
    if (!val) return "";
    let s = String(val).trim();
    if (s.endsWith(".0")) s = s.slice(0, -2);
    return s.replace(/[^\d]/g, "");
  }

  async function ensureBlok2AndUsahaMenuExpanded() {
    FH.log("info", "Menunggu elemen sidebar formulir...");
    await FH.waitFor(SELECTORS.sidebar_container, { timeout: 35000, state: "attached" });

    // 1. Klik Blok II jika belum aktif
    const blok2 = await FH.waitFor(SELECTORS.sidebar_blok_ii, { timeout: 35000 });
    const isExpanded = blok2.parentElement && (
      blok2.parentElement.getAttribute("data-expanded") === "true" ||
      blok2.parentElement.querySelector("div[starts-with(@id, 'collapsible-')]")
    );

    if (!isExpanded) {
      FH.log("info", "Membuka menu 'SE2026 - L BLOK II' di sidebar...");
      await FH.humanClick(blok2);
      await FH.randomSleep(0.7, 1.2);
    }

    // 2. Expand Keterangan Usaha jika ada
    const menuUsaha = FH.find(SELECTORS.sidebar_ket_usaha);
    if (menuUsaha && FH.isVisible(menuUsaha)) {
      const parent = menuUsaha.parentElement;
      const isKetExpanded = parent && (parent.getAttribute("data-expanded") === "true" || parent.querySelector("div[data-expanded='true']"));
      if (!isKetExpanded) {
        FH.log("info", "Membuka sub-menu 'Keterangan Usaha/Perusahaan'...");
        await FH.humanClick(menuUsaha);
        await FH.randomSleep(0.6, 1.0);
      }
    }
  }

  function getValidUsahaItems() {
    const rawItems = FH.findAll("xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[contains(@class, 'cursor-pointer') and @title] | //div[contains(@class, 'cursor-pointer') and @title]");
    return rawItems.filter(item => {
      const title = (item.getAttribute("title") || item.textContent || "").toUpperCase().trim();
      return title && !title.includes("BLOK II") && !title.includes("KETERANGAN USAHA") && !title.includes("CATATAN");
    });
  }

  async function findAndOpenMatchingBusiness(excelKegUtama) {
    await ensureBlok2AndUsahaMenuExpanded();

    const cleanExcelKeg = (excelKegUtama || "").toLowerCase().trim();
    let usahaItems = [];

    for (let attempt = 0; attempt < 8; attempt++) {
      usahaItems = getValidUsahaItems();
      if (usahaItems.length > 0) break;
      await FH.sleep(300);
    }

    if (usahaItems.length === 0) {
      FH.log("info", "Hanya ada 1 usaha atau sub item langsung aktif di formulir.");
      return;
    }

    if (usahaItems.length === 1) {
      FH.log("info", `Ditemukan 1 usaha di Blok II: '${usahaItems[0].getAttribute("title")}'. Membuka...`);
      await FH.humanClick(usahaItems[0]);
      await FH.randomSleep(1.2, 1.8);
      return;
    }

    FH.log("info", `Ditemukan ${usahaItems.length} usaha di Blok II. Mencari usaha yang sesuai dengan kegiatan utama '${cleanExcelKeg.slice(0, 30)}'...`);

    for (let idx = 0; idx < usahaItems.length; idx++) {
      await ensureBlok2AndUsahaMenuExpanded();
      const currentItems = getValidUsahaItems();
      if (idx >= currentItems.length) continue;

      const item = currentItems[idx];
      const itemTitle = item.getAttribute("title") || `Usaha #${idx + 1}`;

      FH.log("info", `[Usaha ${idx + 1}/${currentItems.length}: '${itemTitle}'] Membuka halaman rincian...`);
      await FH.humanClick(item);
      await FH.randomSleep(1.2, 1.8);

      // Periksa field kegiatan utama pada formulir
      const kegField = FH.find(SELECTORS.field_kegiatan_utama);
      let webKeg = "";
      if (kegField) {
        webKeg = (kegField.value || kegField.textContent || "").toLowerCase().trim();
      }

      if (cleanExcelKeg && webKeg && (webKeg.includes(cleanExcelKeg) || cleanExcelKeg.includes(webKeg))) {
        FH.log("info", `[Usaha ${idx + 1}] Kegiatan utama COCOK ('${webKeg.slice(0, 30)}')!`);
        return;
      }
    }

    // Jika tidak ditemukan kesesuaian persis, pilih usaha pertama
    FH.log("warn", "Tidak ditemukan usaha dengan teks kegiatan utama persis, menggunakan usaha pertama.");
    if (usahaItems.length > 0) {
      await FH.humanClick(usahaItems[0]);
      await FH.randomSleep(1.2, 1.8);
    }
  }

  async function fillMasterKBLI(kbliBaru) {
    const kbliClean = await cleanKbliCode(kbliBaru);
    if (!kbliClean) throw new Error("Nilai KBLI Terbaru di Excel kosong!");

    const kbliBox = await FH.waitFor(SELECTORS.container_master_kbli, { timeout: 20000 });
    const targetInput = await FH.waitFor(() => kbliBox.querySelector(SELECTORS.textarea_master_kbli), { timeout: 15000, root: kbliBox });

    FH.log("info", `Mengetikkan KBLI Terbaru '${kbliClean}' ke Master KBLI...`);
    await FH.typeText(targetInput, kbliClean, { delayMs: 40 });

    await FH.sleep(600);
    const loadingDialog = FH.find("div[role='dialog']:has-text('Memuat opsi...'), span:has-text('Memuat opsi...')") || FH.byText("div", "Memuat opsi...");
    if (loadingDialog && FH.isVisible(loadingDialog)) {
      await FH.waitFor(() => !FH.isVisible(loadingDialog), { timeout: 15000 }).catch(() => {});
    }

    let optionElem = document.querySelector(`li[role='option'][data-key='${kbliClean}'], [role='option'][data-key='${kbliClean}']`);
    if (!optionElem) {
      FH.pressKey(targetInput, "ArrowDown", "ArrowDown");
      await FH.randomSleep(0.5, 0.8);
      optionElem = document.querySelector(`li[role='option'][data-key='${kbliClean}'], [role='option'][data-key='${kbliClean}']`) || FH.byText("[role='option'], li[role='option']", kbliClean);
    }

    if (optionElem) {
      FH.log("info", `Memilih opsi KBLI: '${optionElem.textContent.trim().split("\n")[0]}'`);
      await FH.humanClick(optionElem);
      await FH.randomSleep(0.8, 1.2);
    } else {
      FH.log("warn", `Pilihan dropdown KBLI untuk '${kbliClean}' tidak muncul, pengetikan manual tetap dipertahankan.`);
    }
  }

  async function checkAndFillHalal() {
    const halalBox = FH.find(SELECTORS.container_halal);
    if (halalBox && FH.isVisible(halalBox)) {
      if (!FH.isAnyRadioSelected(halalBox)) {
        FH.log("info", "Status Halal kosong, memilih opsi default (3. Tidak Memiliki)...");
        await FH.selectRadioOption(halalBox, "Tidak Memiliki", "3");
      }
    }
  }

  async function checkAndFillIzinEdar() {
    const izinBox = FH.find(SELECTORS.container_izin_edar);
    if (izinBox && FH.isVisible(izinBox)) {
      if (!FH.isAnyRadioSelected(izinBox)) {
        FH.log("info", "Status Izin Edar kosong, memilih opsi default (3. Tidak Memiliki)...");
        await FH.selectRadioOption(izinBox, "Tidak Memiliki", "3");
      }
    }
  }

  async function submitAssignment(debugReview) {
    if (debugReview) {
      FH.log("info", "[Review Mode] Menghentikan otomatis sebelum submit untuk pemeriksaan manual.");
      return "REVIEW_READY";
    }

    const btnKirim = await FH.waitFor(SELECTORS.btn_kirim, { timeout: 25000 });
    FH.log("info", "Mengeklik tombol Kirim formulir...");
    await FH.humanClick(btnKirim, { force: true });
    await FH.randomSleep(1.0, 1.8);

    // Dialog konfirmasi kirim
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
      FH.log("info", "Mengeklik konfirmasi kirim...");
      await FH.humanClick(btnKonfirmasi);
      await FH.randomSleep(1.5, 2.2);
    }

    await FH.waitFor(() => {
      const bodyText = document.body.innerText;
      return bodyText.includes("Berhasil Disubmit") || bodyText.includes("berhasil disimpan") || bodyText.includes("Sukses");
    }, { timeout: 25000 });

    FH.log("info", "Assignment berhasil disubmit dengan sukses.");
    return "SUBMITTED";
  }

  // Task Runner
  FH.tasks.remark_kbli = async function (row, options = {}) {
    const { debugReview = false } = options;
    FH.log("info", `[Remark KBLI] Memulai baris: Assignment ID '${row.assignment_id || "-"}'...`);

    // 1. Temukan dan buka usaha yang cocok
    await findAndOpenMatchingBusiness(row.kegiatan_utama || row.keg_utama || "");

    // 2. Proses Verifikasi KBLI
    const stKbli = String(row.st_kbli || "").trim();
    const kbliBaru = String(row.kbli_baru || row.kbli_terbaru || "").trim();

    // Memberikan catatan #3603 pada rincian Kegiatan Utama (keg_utama) sebelum flag comment KBLI
    const containerKegUtama = FH.find(SELECTORS.container_keg_utama);
    if (containerKegUtama) {
      FH.log("info", "Memberikan catatan '#3603' pada rincian Kegiatan Utama (keg_utama)...");
      await FH.addRemark(containerKegUtama, "#3603");
    }

    const containerKbliGenai = await FH.waitFor(SELECTORS.container_kbli_genai, { timeout: 25000, state: "attached" });

    if (stKbli === "1" || stKbli.toLowerCase().includes("tetap")) {
      FH.log("info", "Kondisi 1: KBLI Tetap -> Memberikan catatan '#0'...");
      await FH.addRemark(containerKbliGenai, "#0");
      await FH.addRemarksToMasterKBLIIfVisible("#0");
    } else if (stKbli === "2" || stKbli.toLowerCase().includes("ganti")) {
      FH.log("info", `Kondisi 2: KBLI Ganti -> Mengisi Master KBLI '${kbliBaru}' & memberikan catatan '#4'...`);
      await fillMasterKBLI(kbliBaru);
      await FH.addRemark(containerKbliGenai, "#4");
      await FH.addRemarksToMasterKBLIIfVisible("#4");
    } else {
      FH.log("info", "Status KBLI tidak spesifik (1/2), memberikan catatan '#0' default...");
      await FH.addRemark(containerKbliGenai, "#0");
      await FH.addRemarksToMasterKBLIIfVisible("#0");
    }

    // 3. Lengkapi Halal & Izin Edar jika ada
    await checkAndFillHalal();
    await checkAndFillIzinEdar();

    // 4. Submit formulir
    const submitResult = await submitAssignment(debugReview);

    return {
      success: true,
      status: "SELESAI",
      keterangan: submitResult === "REVIEW_READY" ? "Siap Ditinjau (Review Mode)" : "Berhasil Diperbarui & Disubmit"
    };
  };
})();
