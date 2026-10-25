// ==============================================================================
// FASIH 3603 HELPER - SIDEPANEL CONTROLLER & UI GLUE
// ==============================================================================

document.addEventListener("DOMContentLoaded", () => {
  // 1. Elemen DOM UI
  const moduleSelect = document.getElementById("module-select");
  const moduleDesc = document.getElementById("module-desc");
  const workerCountSelect = document.getElementById("worker-count");
  const execModeSelect = document.getElementById("exec-mode");

  // Elemen Autentikasi SSO
  const authStatusBadge = document.getElementById("auth-status-badge");
  const authModeSelect = document.getElementById("auth-mode");
  const btnCheckAuth = document.getElementById("btn-check-auth");
  const authCredentialsForm = document.getElementById("auth-credentials-form");
  const ssoUsernameInput = document.getElementById("sso-username");
  const ssoPasswordInput = document.getElementById("sso-password");
  const btnTogglePassword = document.getElementById("btn-toggle-password");
  const btnDoLogin = document.getElementById("btn-do-login");

  const dropZone = document.getElementById("drop-zone");
  const dropText = document.getElementById("drop-text");
  const fileInput = document.getElementById("file-input");
  const fileInfo = document.getElementById("file-info");
  const btnDownloadTemplate = document.getElementById("btn-download-template");

  const btnStart = document.getElementById("btn-start");
  const btnPause = document.getElementById("btn-pause");
  const btnResume = document.getElementById("btn-resume");
  const btnStop = document.getElementById("btn-stop");
  const btnDownloadResult = document.getElementById("btn-download-result");

  const statTotal = document.getElementById("stat-total");
  const statDone = document.getElementById("stat-done");
  const statError = document.getElementById("stat-error");
  const statPending = document.getElementById("stat-pending");
  const progressBar = document.getElementById("progress-bar");
  const progressPct = document.getElementById("progress-pct");
  const progressStatus = document.getElementById("progress-status");

  const tabBtnQueue = document.getElementById("tab-btn-queue");
  const tabBtnLogs = document.getElementById("tab-btn-logs");
  const tabContentQueue = document.getElementById("tab-content-queue");
  const tabContentLogs = document.getElementById("tab-content-logs");

  const tableBody = document.getElementById("table-body");
  const logBox = document.getElementById("log-box");
  const logSearch = document.getElementById("log-search");
  const btnCopyLogs = document.getElementById("btn-copy-logs");
  const btnClearLogs = document.getElementById("btn-clear-logs");

  let allLogs = [];

  // 2. Tampilkan deskripsi modul saat dipilih
  function updateModuleInfo() {
    const modId = moduleSelect.value;
    const config = window.MODULES_CONFIG[modId];
    if (config) {
      moduleDesc.textContent = config.description;
    }
  }
  moduleSelect.addEventListener("change", updateModuleInfo);
  updateModuleInfo();

  // 3. Autentikasi SSO BPS (State & Storage)
  function syncAuthCredentials() {
    const mode = authModeSelect.value;
    const username = (ssoUsernameInput.value || "").trim();
    const password = (ssoPasswordInput.value || "").trim();

    if (mode === "auto") {
      authCredentialsForm.style.display = "block";
    } else {
      authCredentialsForm.style.display = "none";
    }

    const authConfig = { mode, username, password };
    window.Orchestrator.setAuthConfig(authConfig);

    chrome.storage.local.set({
      fasih_auth_config: { mode, username, password }
    });
  }

  // Muat kredensial SSO yang tersimpan
  chrome.storage.local.get(["fasih_auth_config"], (result) => {
    if (result && result.fasih_auth_config) {
      const saved = result.fasih_auth_config;
      if (saved.mode) authModeSelect.value = saved.mode;
      if (saved.username) ssoUsernameInput.value = saved.username;
      if (saved.password) ssoPasswordInput.value = saved.password;
    }
    syncAuthCredentials();
    checkLiveAuthStatus();
  });

  authModeSelect.addEventListener("change", syncAuthCredentials);
  ssoUsernameInput.addEventListener("input", syncAuthCredentials);
  ssoPasswordInput.addEventListener("input", syncAuthCredentials);

  btnTogglePassword.addEventListener("click", () => {
    if (ssoPasswordInput.type === "password") {
      ssoPasswordInput.type = "text";
      btnTogglePassword.textContent = "🔒";
    } else {
      ssoPasswordInput.type = "password";
      btnTogglePassword.textContent = "👁️";
    }
  });

  // Periksa status login tab aktif
  async function checkLiveAuthStatus() {
    authStatusBadge.className = "badge badge-proses";
    authStatusBadge.textContent = "Memeriksa...";

    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      let targetTab = tabs[0];

      if (!targetTab || !targetTab.url || !targetTab.url.includes("bps.go.id")) {
        const fasihTabs = await chrome.tabs.query({ url: "*://fasih-sm.bps.go.id/*" });
        if (fasihTabs.length > 0) targetTab = fasihTabs[0];
      }

      if (!targetTab) {
        authStatusBadge.className = "badge badge-pending";
        authStatusBadge.textContent = "Tab Belum Terbuka";
        return;
      }

      const res = await chrome.tabs.sendMessage(targetTab.id, { type: "CHECK_AUTH_STATUS" });
      if (res && res.success && res.auth) {
        if (res.auth.active && res.auth.status === "LOGGED_IN") {
          authStatusBadge.className = "badge badge-selesai";
          authStatusBadge.textContent = "🟢 Sesi Aktif";
        } else {
          authStatusBadge.className = "badge badge-gagal";
          authStatusBadge.textContent = "🔴 Belum Login";
        }
      } else {
        authStatusBadge.className = "badge badge-pending";
        authStatusBadge.textContent = "Memerlukan Refresh Tab";
      }
    } catch (e) {
      authStatusBadge.className = "badge badge-pending";
      authStatusBadge.textContent = "Siap Dihubungkan";
    }
  }

  btnCheckAuth.addEventListener("click", checkLiveAuthStatus);

  // Tombol Login SSO Sekarang
  btnDoLogin.addEventListener("click", async () => {
    const username = (ssoUsernameInput.value || "").trim();
    const password = (ssoPasswordInput.value || "").trim();

    if (!username || !password) {
      alert("Harap isikan Username dan Password SSO BPS terlebih dahulu!");
      return;
    }

    try {
      btnDoLogin.disabled = true;
      btnDoLogin.textContent = "⏳ Sedang Login...";

      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      let targetTab = tabs[0];
      if (!targetTab || !targetTab.url || !targetTab.url.includes("bps.go.id")) {
        const fasihTabs = await chrome.tabs.query({ url: "*://fasih-sm.bps.go.id/*" });
        if (fasihTabs.length > 0) targetTab = fasihTabs[0];
      }

      if (!targetTab) {
        targetTab = await chrome.tabs.create({ url: "https://fasih-sm.bps.go.id/app", active: true });
        await new Promise((r) => setTimeout(r, 2000));
      }

      log("info", `[Auth Manager] Memulai proses login untuk '${username}'...`);
      const res = await chrome.tabs.sendMessage(targetTab.id, {
        type: "PERFORM_AUTO_LOGIN",
        payload: { username, password }
      });

      if (res && res.success) {
        log("info", "✨ Login SSO BPS berhasil diselesaikan!");
        alert("Berhasil login ke portal Fasih BPS!");
        checkLiveAuthStatus();
      } else {
        throw new Error(res?.error || "Gagal melakukan login SSO");
      }
    } catch (err) {
      log("error", `Gagal login SSO: ${err.message}`);
      alert(`Login Gagal:\n${err.message}`);
    } finally {
      btnDoLogin.disabled = false;
      btnDoLogin.textContent = "🔑 Login SSO Sekarang";
    }
  });

  // 4. Tab Switching
  tabBtnQueue.addEventListener("click", () => {
    tabBtnQueue.classList.add("active");
    tabBtnLogs.classList.remove("active");
    tabContentQueue.classList.add("active");
    tabContentLogs.classList.remove("active");
  });

  tabBtnLogs.addEventListener("click", () => {
    tabBtnLogs.classList.add("active");
    tabBtnQueue.classList.remove("active");
    tabContentLogs.classList.add("active");
    tabContentQueue.classList.remove("active");
  });

  // 5. File Upload (Click & Drag-and-Drop)
  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleSelectedFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleSelectedFile(e.target.files[0]);
    }
  });

  async function handleSelectedFile(file) {
    if (!file.name.endsWith(".xlsx") && !file.name.endsWith(".xls")) {
      alert("Harap pilih file dokumen Excel dengan format .xlsx atau .xls!");
      return;
    }

    try {
      dropText.textContent = "Membaca & memvalidasi file Excel...";
      const modId = moduleSelect.value;
      const res = await window.ExcelIO.parseExcelFile(file, modId);

      fileInfo.style.display = "block";
      fileInfo.textContent = `✅ ${file.name} (${res.totalRows} baris terdeteksi)`;
      dropText.textContent = "File Excel siap diproses";

      // Update statistik awal
      statTotal.textContent = res.totalRows;
      statDone.textContent = res.doneRows;
      statError.textContent = "0";
      statPending.textContent = res.pendingRows;

      const pct = res.totalRows > 0 ? Math.round((res.doneRows / res.totalRows) * 100) : 0;
      progressBar.style.width = `${pct}%`;
      progressPct.textContent = `${pct}%`;
      progressStatus.textContent = `${res.pendingRows} baris siap diproses`;

      renderTable(res.rows);

      btnStart.disabled = false;
      btnDownloadResult.disabled = false;

      log("info", `File '${file.name}' berhasil dimuat: ${res.totalRows} baris (${res.doneRows} selesai, ${res.pendingRows} antrean).`);
    } catch (err) {
      dropText.textContent = "Gagal memproses file. Klik untuk mencoba lagi.";
      fileInfo.style.display = "none";
      btnStart.disabled = true;
      alert(`Validasi Excel Gagal:\n${err.message}`);
      log("error", `Gagal memuat Excel: ${err.message}`);
    }
  }

  // 6. Render Tabel Antrean
  function renderTable(rows) {
    tableBody.innerHTML = "";
    if (!rows || rows.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="5" class="empty-cell">Tidak ada baris data.</td></tr>`;
      return;
    }

    const fragment = document.createDocumentFragment();
    rows.forEach((r, idx) => {
      const tr = document.createElement("tr");
      tr.id = `row-${r._rowIndex}`;

      let badgeClass = "badge-pending";
      let badgeText = "Pending";
      const st = (r.status || "").toUpperCase();

      if (st === "SELESAI" || st === "SUCCESS" || st === "BERHASIL") {
        badgeClass = "badge-selesai";
        badgeText = "Selesai";
      } else if (st === "PROSES") {
        badgeClass = "badge-proses";
        badgeText = "Proses";
      } else if (st === "GAGAL" || st === "ERROR") {
        badgeClass = "badge-gagal";
        badgeText = "Gagal";
      }

      const infoText = r.kegiatan_utama || r.nama || r.nama_usaha || "-";

      tr.innerHTML = `
        <td style="text-align: center;">${idx + 1}</td>
        <td><strong>${r.assignment_id || "-"}</strong></td>
        <td>${infoText}</td>
        <td><span class="badge ${badgeClass}">${badgeText}</span></td>
        <td class="cell-ket">${r.keterangan || "-"}</td>
      `;
      fragment.appendChild(tr);
    });

    tableBody.appendChild(fragment);
  }

  // 7. Logging UI
  function log(level, message) {
    const time = new Date().toLocaleTimeString("id-ID", { hour12: false });
    const entry = { time, level, message };
    allLogs.push(entry);

    const filter = logSearch.value.toLowerCase().trim();
    if (!filter || message.toLowerCase().includes(filter)) {
      appendLogElement(entry);
    }
  }

  function appendLogElement(entry) {
    const div = document.createElement("div");
    div.className = "log-entry";
    div.innerHTML = `
      <span class="log-time">[${entry.time}]</span>
      <span class="log-${entry.level}">[${entry.level.toUpperCase()}]</span>
      <span>${entry.message}</span>
    `;
    logBox.appendChild(div);
    logBox.scrollTop = logBox.scrollHeight;
  }

  logSearch.addEventListener("input", () => {
    logBox.innerHTML = "";
    const filter = logSearch.value.toLowerCase().trim();
    allLogs.forEach((entry) => {
      if (!filter || entry.message.toLowerCase().includes(filter)) {
        appendLogElement(entry);
      }
    });
  });

  btnCopyLogs.addEventListener("click", () => {
    const text = allLogs.map((l) => `[${l.time}] [${l.level.toUpperCase()}] ${l.message}`).join("\n");
    navigator.clipboard.writeText(text).then(() => {
      alert("Seluruh log berhasil disalin ke clipboard!");
    });
  });

  btnClearLogs.addEventListener("click", () => {
    allLogs = [];
    logBox.innerHTML = "";
  });

  // 8. Unduh Template & Hasil
  btnDownloadTemplate.addEventListener("click", () => {
    try {
      window.ExcelIO.downloadTemplate(moduleSelect.value);
    } catch (e) {
      alert(`Gagal mengunduh template: ${e.message}`);
    }
  });

  btnDownloadResult.addEventListener("click", () => {
    try {
      window.ExcelIO.downloadUpdatedExcel();
    } catch (e) {
      alert(`Gagal mengunduh hasil: ${e.message}`);
    }
  });

  // 9. Inisialisasi Orchestrator & Callbacks
  window.Orchestrator.init({
    onStatusChange(state) {
      if (state === "RUNNING") {
        btnStart.style.display = "none";
        btnPause.style.display = "block";
        btnResume.style.display = "none";
        btnStop.style.display = "block";
        moduleSelect.disabled = true;
        workerCountSelect.disabled = true;
        execModeSelect.disabled = true;
      } else if (state === "PAUSED") {
        btnPause.style.display = "none";
        btnResume.style.display = "block";
        btnStop.style.display = "block";
      } else if (state === "IDLE" || state === "COMPLETED") {
        btnStart.style.display = "block";
        btnStart.disabled = false;
        btnPause.style.display = "none";
        btnResume.style.display = "none";
        btnStop.style.display = "none";
        moduleSelect.disabled = false;
        workerCountSelect.disabled = false;
        execModeSelect.disabled = false;
      }
    },

    onProgress(stats) {
      statTotal.textContent = stats.total;
      statDone.textContent = stats.done;
      statError.textContent = stats.error;
      statPending.textContent = stats.pending;

      const pct = stats.total > 0 ? Math.round(((stats.done + stats.error) / stats.total) * 100) : 0;
      progressBar.style.width = `${pct}%`;
      progressPct.textContent = `${pct}%`;
      progressStatus.textContent = `${stats.done} selesai &bull; ${stats.error} gagal &bull; ${stats.pending} sisa`;
    },

    onRowUpdate(rowIndex, status, keterangan) {
      const tr = document.getElementById(`row-${rowIndex}`);
      if (tr) {
        const badgeCell = tr.cells[3];
        const ketCell = tr.cells[4];

        let badgeClass = "badge-pending";
        let badgeText = "Pending";
        const st = (status || "").toUpperCase();

        if (st === "SELESAI") {
          badgeClass = "badge-selesai";
          badgeText = "Selesai";
        } else if (st === "PROSES") {
          badgeClass = "badge-proses";
          badgeText = "Proses";
        } else if (st === "GAGAL" || st === "ERROR") {
          badgeClass = "badge-gagal";
          badgeText = "Gagal";
        }

        badgeCell.innerHTML = `<span class="badge ${badgeClass}">${badgeText}</span>`;
        ketCell.textContent = keterangan || "-";
      }
    },

    onLog(logEntry) {
      log(logEntry.level, logEntry.message);
    }
  });

  // 10. Tombol Kontrol Otomasi
  btnStart.addEventListener("click", () => {
    const modId = moduleSelect.value;
    const workers = parseInt(workerCountSelect.value, 10) || 1;
    const isReview = execModeSelect.value === "review";

    window.Orchestrator.start({
      moduleId: modId,
      workerCount: workers,
      debugReview: isReview
    });
  });

  btnPause.addEventListener("click", () => {
    window.Orchestrator.pause();
  });

  btnResume.addEventListener("click", () => {
    window.Orchestrator.resume();
  });

  btnStop.addEventListener("click", () => {
    window.Orchestrator.stop();
  });
});
