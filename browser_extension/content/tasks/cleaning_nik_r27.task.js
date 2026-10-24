// ==============================================================================
// FASIH 3603 HELPER - TASK: DATA CLEANING NIK R27 SE2026
// Paritas 100% dengan modules/cleaning_nik_r27/engine.py
// ==============================================================================

(function () {
  const FH = window.FH;

  const SELECTORS = {
    sidebar_container: ".fasih-form-sidebar, div[class*='sidebar']",
    sidebar_blok_i: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='SE2026 - L BLOK I' or contains(@title, 'BLOK I') or contains(text(), 'BLOK I')] | //*[@title='SE2026 - L BLOK I' or contains(@title, 'BLOK I') or contains(text(), 'BLOK I')]",
    sidebar_ket_art: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//div[@title='Keterangan Anggota Keluarga' or contains(text(), 'Keterangan Anggota Keluarga')]",
    sidebar_blok_catatan: "xpath=//div[contains(@class, 'fasih-form-sidebar')]//*[@title='CATATAN' or normalize-space(text())='CATATAN' or contains(text(), 'CATATAN')] | //*[@title='CATATAN' or normalize-space(text())='CATATAN']",
    container_nik: "div[id^='nik_dtsen#'], div[id*='nik_dtsen']",
    input_nik: "input[type='text'], input",
    btn_kirim: "button#btn-kirim, button:has-text('Kirim')"
  };

  function cleanNik(val) {
    if (!val) return "";
    let s = String(val).trim();
    if (s.endsWith(".0")) s = s.slice(0, -2);
    return s.replace(/[^\d]/g, "");
  }

  function normalizeText(text) {
    if (!text) return "";
    return String(text).replace(/\u00a0/g, " ").trim().toLowerCase().replace(/\s+/g, " ");
  }

  function getValidArtItems() {
    const rawItems = FH.findAll(
      "xpath=//div[@title='Keterangan Anggota Keluarga']/following-sibling::div//div[contains(@class, 'fasih-form-sidebar')]/div[contains(@class, 'cursor-pointer') and @title] | " +
      "//div[@title='Keterangan Anggota Keluarga']/following-sibling::div//div[contains(@class, 'cursor-pointer') and @title]"
    );

    const valid = [];
    const skipList = ["SE2026 - L BLOK I", "KETERANGAN ANGGOTA KELUARGA", "CATATAN", "KETERANGAN UMUM KELUARGA", "KETERANGAN PEMBERI JAWABAN"];

    for (const item of rawItems) {
      const title = (item.getAttribute("title") || item.textContent || "").trim();
      const upper = title.toUpperCase();
      if (!title || skipList.some(skip => upper.includes(skip))) continue;
      valid.push({ element: item, title });
    }
    return valid;
  }

  async function ensureBlok1AndArtMenuExpanded() {
    FH.log("info", "Menunggu elemen sidebar formulir...");
    await FH.waitFor(SELECTORS.sidebar_container, { timeout: 35000, state: "attached" });

    const blok1 = await FH.waitFor(SELECTORS.sidebar_blok_i, { timeout: 35000 });
    const isExpanded = document.querySelector("//div[contains(@class, 'fasih-form-sidebar')]//div[@title='SE2026 - L BLOK I' or contains(@title, 'BLOK I')]/following-sibling::div[@data-expanded]");
    if (!isExpanded) {
      FH.log("info", "Membuka menu Blok I (Keterangan Umum Keluarga) di sidebar...");
      await FH.humanClick(blok1);
      await FH.randomSleep(0.8, 1.2);
    }

    const menuArt = FH.find(SELECTORS.sidebar_ket_art);
    if (menuArt && FH.isVisible(menuArt)) {
      const parent = menuArt.parentElement;
      const isKetExpanded = parent && (parent.getAttribute("data-expanded") === "true" || parent.querySelector("div[data-expanded='true']"));
      if (!isKetExpanded) {
        FH.log("info", "Membuka sub-menu 'Keterangan Anggota Keluarga'...");
        await FH.humanClick(menuArt);
        await FH.randomSleep(0.6, 1.0);
      }
    }
  }

  async function submitCleaningNIKR27(debugReview) {
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

    // 3. Klik Kirim Formulir
    const btnKirim = await FH.waitFor(SELECTORS.btn_kirim, { timeout: 25000 });
    FH.log("info", "Mengklik tombol Kirim formulir...");
    await FH.humanClick(btnKirim, { force: true });
    await FH.randomSleep(1.0, 1.8);

    // 4. Periksa dialog validasi Kirim & hitung Galat
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
      throw new Error(`Terdapat ${galatCount} Galat pada formulir. Submit dibatalkan.`);
    }

    const btnKirimDialog = FH.find("button:has-text('Kirim')", dialogValidasi);
    if (btnKirimDialog && FH.isVisible(btnKirimDialog)) {
      await FH.humanClick(btnKirimDialog);
      await FH.randomSleep(1.2, 1.8);
    }

    // 5. Konfirmasi Kirim
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
      FH.log("info", "Mengklik Konfirmasi Kirim...");
      await FH.humanClick(btnKonfirmasi);
      await FH.randomSleep(1.5, 2.2);
    }

    // 6. Tunggu dialog sukses
    await FH.waitFor(() => {
      const txt = document.body.innerText;
      return txt.includes("Berhasil Disubmit") || txt.includes("berhasil disimpan") || txt.includes("Sukses");
    }, { timeout: 25000 });

    FH.log("info", "Formulir penugasan berhasil disubmit dengan sukses.");
    return "SUBMITTED";
  }

  FH.tasks.cleaning_nik_r27 = async function (row, options = {}) {
    const { debugReview = false } = options;
    FH.log("info", `[Cleaning NIK R27] Memulai baris: Assignment '${row.assignment_id || row.id || "-"}'...`);

    // Ekstrak target NIK dari data baris Excel
    let targetNiks = [];
    if (Array.isArray(row.target_niks) && row.target_niks.length > 0) {
      targetNiks = row.target_niks;
    } else if (Array.isArray(row.nik_list) && row.nik_list.length > 0) {
      targetNiks = row.nik_list;
    } else {
      for (const [k, v] of Object.entries(row)) {
        if (/^nik(?:_|\s*)?(\d+)?$/i.test(k) && v) {
          targetNiks.push(String(v));
        }
      }
      if (targetNiks.length === 0 && row._raw) {
        for (const [k, v] of Object.entries(row._raw)) {
          if (/^nik(?:_|\s*)?(\d+)?$/i.test(k) && v) {
            targetNiks.push(String(v));
          }
        }
      }
    }

    const cleanTargets = new Set();
    for (const n of targetNiks) {
      const cn = cleanNik(n);
      if (cn) cleanTargets.add(cn);
    }

    if (cleanTargets.size === 0) {
      throw new Error("Target NIK kosong pada baris ini!");
    }

    FH.log("info", `Target NIK yang harus diremark (#0): [${Array.from(cleanTargets).join(", ")}] (${cleanTargets.size} NIK)...`);

    await ensureBlok1AndArtMenuExpanded();

    let artItems = [];
    for (let r = 0; r < 15; r++) {
      artItems = getValidArtItems();
      if (artItems.length > 0) break;
      await FH.sleep(400);
    }

    if (artItems.length === 0) {
      throw new Error("Tidak ditemukan daftar anggota keluarga (ART) di sidebar");
    }

    FH.log("info", `Ditemukan ${artItems.length} anggota keluarga di web. Memulai pengecekan NIK...`);

    const matchedNiks = new Map();

    for (let idx = 0; idx < artItems.length; idx++) {
      if (FH.state.shouldStop) return;

      const art = artItems[idx];
      FH.log("info", `[ART ${idx + 1}/${artItems.length}] Membuka formulir ART '${art.title}'...`);

      await FH.humanClick(art.element);
      await FH.randomSleep(1.2, 1.8);

      const nikBox = await FH.waitFor(SELECTORS.container_nik, { timeout: 20000, state: "attached" });
      if (!nikBox) {
        FH.log("warn", `Container nik_dtsen tidak ditemukan pada ART '${art.title}'. Lanjut...`);
        continue;
      }

      const inputNik = nikBox.querySelector(SELECTORS.input_nik);
      let webNikRaw = "";
      if (inputNik) {
        webNikRaw = inputNik.value || inputNik.getAttribute("value") || "";
      }
      const webNikClean = cleanNik(webNikRaw);

      FH.log("info", `ART '${art.title}' -> NIK Web: '${webNikClean || "KOSONG"}'`);

      if (cleanTargets.has(webNikClean)) {
        FH.log("info", `✨ NIK COCOK! Memberikan remarks '#0' pada NIK ${webNikClean} (ART: '${art.title}')...`);
        await FH.addRemark(nikBox, "#0");
        matchedNiks.set(webNikClean, art.title);

        if (matchedNiks.size >= cleanTargets.size) {
          FH.log("info", `🚀 Seluruh target NIK (${matchedNiks.size} NIK) berhasil ditemukan!`);
          break;
        }
      }
    }

    const missingNiks = Array.from(cleanTargets).filter(cn => !matchedNiks.has(cn));
    if (missingNiks.length > 0) {
      throw new Error(`Hanya ${matchedNiks.size} dari ${cleanTargets.size} NIK sasaran ditemukan di web. Belum ditemukan: [${missingNiks.join(", ")}]`);
    }

    // Submit
    const submitResult = await submitCleaningNIKR27(debugReview);

    return {
      success: true,
      status: "SELESAI",
      keterangan: submitResult === "REVIEW_READY" ? "Siap Ditinjau (Review Mode)" : `Pembersihan NIK R27 Berhasil (${matchedNiks.size} NIK diremark #0) & Disubmit`
    };
  };
})();
