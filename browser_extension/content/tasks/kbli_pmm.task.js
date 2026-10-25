// ==============================================================================
// FASIH 3603 HELPER - TASK: KBLI PMM SE2026 (56101 & 56102)
// Paritas 100% dengan modules/kbli_pmm/engine.py
// ==============================================================================

(function () {
  const FH = window.FH;

  const SELECTORS = {
    sidebar_container: ".fasih-form-sidebar, div[class*='sidebar']",
    sidebar_blok_ii: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')] | //*[@title='SE2026 - L BLOK II' or contains(@title, 'BLOK II') or contains(text(), 'BLOK II')]",
    sidebar_ket_usaha: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[@title='Keterangan Usaha/Perusahaan' or text()='Keterangan Usaha/Perusahaan']",
    field_kegiatan_utama: "div[id^='keg_utama#'] input[type='text'], div[id^='keg_utama#'] textarea, div[id*='keg_utama'] input, div[id^='kegiatan_utama#'] textarea, div[id^='kegiatan_utama#'] input, textarea#kegiatan_utama, input#kegiatan_utama",
    container_produk_sendiri: "div[id^='produk_sendiri#'], div[id='produk_sendiri']",
    container_layanan_mamin: "div[id^='layanan_mamin#'], div[id='layanan_mamin']",
    container_lokasi_usaha: "div[id^='lokasi_usaha#'], div[id='lokasi_usaha']",
    container_kbli_genai: "div[id^='kbli_genai#'], div[id='kbli_genai']",
    container_master_kbli: "div[id^='kbli#'], div[id='kbli']",
    textarea_master_kbli: "input[type='text'], textarea",
    container_halal: "div[id^='halal#'], div[id='halal']",
    container_izin_edar: "div[id^='izin_edar#'], div[id='izin_edar']",
    btn_kirim: "button#btn-kirim, button:has-text('Kirim')"
  };

  async function cleanKbli(val) {
    if (!val) return "";
    let s = String(val).trim();
    if (s.endsWith(".0")) s = s.slice(0, -2);
    return s.replace(/[^\d]/g, "");
  }

  async function openUsahaMenu(excelKegUtama) {
    FH.log("info", "Menunggu elemen sidebar formulir...");
    await FH.waitFor(SELECTORS.sidebar_container, { timeout: 35000, state: "attached" });

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

    const cleanExcelKeg = (excelKegUtama || "").toLowerCase().trim();
    const rawItems = FH.findAll("xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[contains(@class, 'cursor-pointer') and @title] | //div[contains(@class, 'cursor-pointer') and @title]");
    const usahaItems = rawItems.filter(item => {
      const title = (item.getAttribute("title") || item.textContent || "").toUpperCase().trim();
      return title && !title.includes("BLOK II") && !title.includes("KETERANGAN USAHA") && !title.includes("CATATAN");
    });

    if (usahaItems.length === 0) return;

    if (usahaItems.length === 1) {
      FH.log("info", `Ditemukan 1 usaha di Blok II: '${usahaItems[0].getAttribute("title")}'. Membuka...`);
      await FH.humanClick(usahaItems[0]);
      await FH.randomSleep(1.2, 1.8);
      return;
    }

    FH.log("info", `Ditemukan ${usahaItems.length} usaha di Blok II. Mencocokkan '${cleanExcelKeg.slice(0, 30)}'...`);
    for (let idx = 0; idx < usahaItems.length; idx++) {
      const item = usahaItems[idx];
      await FH.humanClick(item);
      await FH.randomSleep(1.2, 1.8);

      const kegField = FH.find(SELECTORS.field_kegiatan_utama);
      let webKeg = "";
      if (kegField) {
        webKeg = (kegField.value || kegField.textContent || "").toLowerCase().trim();
      }

      if (cleanExcelKeg && webKeg && (webKeg.includes(cleanExcelKeg) || cleanExcelKeg.includes(webKeg))) {
        FH.log("info", `[Usaha ${idx + 1}] Kegiatan utama PMM COCOK ('${webKeg.slice(0, 30)}')!`);
        return;
      }
    }

    if (usahaItems.length > 0) {
      await FH.humanClick(usahaItems[0]);
      await FH.randomSleep(1.2, 1.8);
    }
  }

  async function fillMasterKBLI(kbliBaru) {
    const kbliClean = await cleanKbli(kbliBaru);
    if (!kbliClean) throw new Error("KBLI Terbaru di Excel kosong!");

    const kbliBox = await FH.waitFor(SELECTORS.container_master_kbli, { timeout: 20000 });
    const targetInput = await FH.waitFor(() => kbliBox.querySelector(SELECTORS.textarea_master_kbli), { timeout: 15000, root: kbliBox });

    FH.log("info", `Mengetikkan KBLI PMM '${kbliClean}' ke Master KBLI...`);
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
      FH.log("info", `Memilih opsi KBLI PMM: '${optionElem.textContent.trim().split("\n")[0]}'`);
      await FH.humanClick(optionElem);
      await FH.randomSleep(0.8, 1.2);
    }
  }

  async function processPMMCharacteristics(kbliAkhir) {
    FH.log("info", "Memproses rincian karakteristik PMM...");

    // 1. Rincian 13.b1: Apakah memproduksi barang sendiri -> 2. Tidak
    const boxProduk = await FH.waitFor(SELECTORS.container_produk_sendiri, { timeout: 20000 });
    FH.log("info", "Rincian 13.b1: Mengisi '2. Tidak'...");
    await FH.selectRadioOption(boxProduk, "Tidak", "2");
    await FH.randomSleep(0.5, 0.8);

    // 2. Rincian 13.b: Menyediakan layanan makan minum -> 1. Ya
    const boxMamin = await FH.waitFor(SELECTORS.container_layanan_mamin, { timeout: 20000 });
    FH.log("info", "Rincian 13.b: Mengisi '1. Ya'...");
    await FH.selectRadioOption(boxMamin, "Ya", "1");
    await FH.randomSleep(0.8, 1.4);

    // 3. Rincian 13.c: Lokasi Usaha (Menunggu dinamis setelah 13.b diisi)
    FH.log("info", "Menunggu rincian 13.c (Lokasi Usaha) muncul di formulir...");
    const boxLokasi = await FH.waitFor(SELECTORS.container_lokasi_usaha, { timeout: 25000 });
    await FH.randomSleep(0.6, 1.0);

    const kbliClean = String(kbliAkhir || "").trim();

    function checkKelilingWarning(boxEl) {
      if (!boxEl) return false;
      // 1. Periksa teks langsung di boxLokasi
      const boxText = (boxEl.innerText || boxEl.textContent || "").toLowerCase();
      if (
        (boxText.includes("usaha keliling") && boxText.includes("r.9a")) ||
        (boxText.includes("r.13c") && boxText.includes("kode 10")) ||
        (boxText.includes("kode 10") && boxText.includes("keliling")) ||
        boxText.includes("r.9a diisi kode 2")
      ) {
        return true;
      }
      // 2. Periksa elemen destructive / alert di dalam boxLokasi
      const warningElements = boxEl.querySelectorAll("div[class*='text-destructive'], span, p, div[class*='destructive'], *[role='alert']");
      for (const w of warningElements) {
        if (!FH.isVisible(w)) continue;
        const txt = (w.textContent || "").toLowerCase();
        if (txt.includes("usaha keliling") || txt.includes("r.9a diisi kode 2") || txt.includes("kode 10") || txt.includes("r.13c")) {
          return true;
        }
      }
      // 3. Fallback periksa elemen warning di dokumen terkait R.9a / 13c
      const pageWarnings = document.querySelectorAll("div[id^='lokasi_usaha'] div[class*='text-destructive'], div[class*='text-destructive']");
      for (const pw of pageWarnings) {
        if (!FH.isVisible(pw)) continue;
        const ptxt = (pw.textContent || "").toLowerCase();
        if (ptxt.includes("r.9a diisi kode 2") || (ptxt.includes("usaha keliling") && ptxt.includes("r.13c"))) {
          return true;
        }
      }
      return false;
    }

    if (kbliClean === "56101") {
      FH.log("info", "KBLI 56101 -> Memilih lokasi usaha '9. Restoran, warung makan, sejenisnya'...");
      await FH.selectRadioOption(boxLokasi, "Restoran", "09");
    } else if (kbliClean === "56102") {
      // Validasi khusus 56102 (Tahap 1: Pre-selection check):
      // Jika peringatan Usaha Keliling (R.9a=2) sudah tampak sebelumnya, langsung pilih 10. Keliling
      const hasWarningPre = checkKelilingWarning(boxLokasi);

      if (hasWarningPre) {
        FH.log("warn", "[13. c] Terdeteksi peringatan Usaha Keliling (R.9a=2)! Memilih lokasi '10. Keliling'...");
        await FH.selectRadioOption(boxLokasi, "Keliling", "10");
      } else {
        FH.log("info", "[13. c] KBLI 56102 Standar -> Memilih lokasi usaha '5. Kedai, stan, tenda'...");
        await FH.selectRadioOption(boxLokasi, "Kedai", "05");

        // Validasi khusus 56102 (Tahap 2: Post-selection check):
        // Beri jeda formulir Fasih melakukan validasi silang (cross-validation).
        // Jika muncul pesan peringatan Usaha Keliling (R.9a=2), langsung koreksi dan alihkan ke 10. Keliling!
        await FH.randomSleep(0.6, 1.0);
        const hasWarningPost = checkKelilingWarning(boxLokasi);
        if (hasWarningPost) {
          FH.log("warn", "[13. c] ⚠️ Terdeteksi validasi peringatan Usaha Keliling (R.9a=2) setelah memilih Kedai! Mengoreksi dan mengalihkan ke '10. Keliling'...");
          await FH.selectRadioOption(boxLokasi, "Keliling", "10");
          await FH.randomSleep(0.5, 0.8);
          FH.log("info", "[13. c] ✅ Berhasil mengoreksi lokasi usaha ke '10. Keliling'. Peringatan terselesaikan.");
        }
      }
    } else {
      FH.log("warn", `KBLI '${kbliClean}' di luar 56101/56102. Mencoba memilih lokasi restoran/kedai...`);
      try {
        await FH.selectRadioOption(boxLokasi, "Restoran", "09");
      } catch (e) {
        await FH.selectRadioOption(boxLokasi, "Kedai", "05");
      }
    }
  }

  FH.tasks.kbli_pmm = async function (row, options = {}) {
    const { debugReview = false } = options;
    FH.log("info", `[KBLI PMM] Memulai baris: Assignment '${row.assignment_id || "-"}'...`);

    await openUsahaMenu(row.kegiatan_utama || row.keg_utama || "");

    const kbliAkhir = String(row.kbli_akhir || row.kbli_baru || "").trim();
    const stKbli = String(row.st_kbli || "").trim();

    // 1. Proses karakteristik 13.b1, 13.b, 13.c lokasi usaha
    await processPMMCharacteristics(kbliAkhir);

    // 2. Remark & Master KBLI
    const containerGenai = await FH.waitFor(SELECTORS.container_kbli_genai, { timeout: 25000, state: "attached" });

    if (stKbli === "1" || stKbli.toLowerCase().includes("tetap")) {
      FH.log("info", "Kondisi 1: KBLI PMM Tetap -> Memberikan catatan '#0'...");
      await FH.addRemark(containerGenai, "#0");
      await FH.addRemarksToMasterKBLIIfVisible("#0");
    } else {
      FH.log("info", `Kondisi 2: KBLI PMM Ganti -> Mengisi Master KBLI '${kbliAkhir}' & catatan '#4'...`);
      await fillMasterKBLI(kbliAkhir);
      await FH.addRemark(containerGenai, "#4");
      await FH.addRemarksToMasterKBLIIfVisible("#4");
    }

    // 3. Halal & Izin Edar
    const halalBox = FH.find(SELECTORS.container_halal);
    if (halalBox && FH.isVisible(halalBox) && !FH.isAnyRadioSelected(halalBox)) {
      await FH.selectRadioOption(halalBox, "Tidak Memiliki", "3");
    }

    const izinBox = FH.find(SELECTORS.container_izin_edar);
    if (izinBox && FH.isVisible(izinBox) && !FH.isAnyRadioSelected(izinBox)) {
      await FH.selectRadioOption(izinBox, "Tidak Memiliki", "3");
    }

    if (debugReview) {
      FH.log("info", "[Review Mode] Siap untuk ditinjau manual.");
      return { success: true, status: "SELESAI", keterangan: "Siap Ditinjau (Review Mode)" };
    }

    // 4. Submit
    const btnKirim = await FH.waitFor(SELECTORS.btn_kirim, { timeout: 25000 });
    await FH.humanClick(btnKirim, { force: true });
    await FH.randomSleep(1.0, 1.8);

    const btnKonfirmasi = await FH.waitFor(() => {
      return (
        FH.find("div:has-text('Konfirmasi Kirim') button:has-text('Konfirmasi')") ||
        FH.find("div:has-text('Apakah Anda yakin') button:has-text('Konfirmasi')") ||
        FH.find("button:has-text('Konfirmasi')") ||
        FH.byText("button", "Konfirmasi") ||
        FH.byText("button", "Ya")
      );
    }, { timeout: 20000 });

    if (btnKonfirmasi) {
      await FH.humanClick(btnKonfirmasi);
      await FH.randomSleep(1.5, 2.2);
    }

    await FH.waitFor(() => {
      const txt = document.body.innerText;
      return txt.includes("Berhasil Disubmit") || txt.includes("berhasil disimpan") || txt.includes("Sukses");
    }, { timeout: 25000 });

    return { success: true, status: "SELESAI", keterangan: "KBLI PMM Berhasil Diperbarui & Disubmit" };
  };
})();
