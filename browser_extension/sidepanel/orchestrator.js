// ==============================================================================
// FASIH 3603 HELPER - ORCHESTRATOR & MULTI-TAB WORKER POOL
// ==============================================================================

window.Orchestrator = {
  state: "IDLE", // IDLE, RUNNING, PAUSED, STOPPING, COMPLETED
  moduleId: "remark_kbli",
  workerCount: 1,
  debugReview: false,

  // Konfigurasi Autentikasi SSO BPS (Paritas dengan core/browser_manager.py)
  authConfig: {
    mode: "manual", // "manual" | "auto"
    username: "",
    password: ""
  },

  // Antrean data
  queue: [],
  currentIndex: 0,
  activeWorkers: {}, // workerId -> { tabId, currentRow }

  // Statistik
  stats: { total: 0, done: 0, error: 0, pending: 0 },

  // Event callbacks UI
  onStatusChange: null,
  onProgress: null,
  onLog: null,
  onRowUpdate: null,

  // 1. Inisialisasi
  init(callbacks = {}) {
    this.onStatusChange = callbacks.onStatusChange || (() => {});
    this.onProgress = callbacks.onProgress || (() => {});
    this.onLog = callbacks.onLog || (() => {});
    this.onRowUpdate = callbacks.onRowUpdate || (() => {});

    // Tangkap pesan dari tab worker
    chrome.runtime.onMessage.addListener(async (message, sender) => {
      if (message.type === "SESSION_EXPIRED") {
        this.log("warn", `[Auth Guard] ${message.payload.reason}`);

        // Jika mode Auto-Login SSO aktif dan kredensial terisi -> Coba Re-autentikasi otomatis
        if (this.authConfig.mode === "auto" && this.authConfig.username && this.authConfig.password && sender.tab?.id) {
          this.log("info", `[Auth Manager] Mencoba Auto-Login SSO otomatis untuk tab ${sender.tab.id}...`);
          try {
            await this.performAutoLoginOnTab(sender.tab.id);
            this.log("info", "[Auth Manager] Auto-Login berhasil diselesaikan. Melanjutkan tugas...");
            return;
          } catch (autoErr) {
            this.log("error", `[Auth Manager] Auto-Login gagal: ${autoErr.message}`);
          }
        }

        this.pause();
        alert(`Perhatian: ${message.payload.reason}\nSilakan periksa atau login kembali di browser, lalu klik 'Lanjut'.`);
      } else if (message.type === "LOG_STREAM") {
        this.log(message.payload.level, message.payload.message);
      }
    });
  },

  setAuthConfig(cfg) {
    this.authConfig = { ...this.authConfig, ...cfg };
  },

  log(level, msg) {
    const time = new Date().toLocaleTimeString("id-ID", { hour12: false });
    if (this.onLog) {
      this.onLog({ timestamp: time, level, message: msg });
    }
  },

  setState(newState) {
    this.state = newState;
    if (this.onStatusChange) this.onStatusChange(newState);
  },

  // 2. Mulai Otomasi
  async start(options = {}) {
    if (this.state === "RUNNING") return;

    this.moduleId = options.moduleId || this.moduleId;
    this.workerCount = Math.max(1, Math.min(3, options.workerCount || 1));
    this.debugReview = !!options.debugReview;

    // Ambil baris yang belum selesai
    const allRows = window.ExcelIO.normalizedRows || [];
    this.queue = allRows.filter((r) => !r._isDone);

    this.stats = {
      total: allRows.length,
      done: allRows.filter((r) => r._isDone).length,
      error: 0,
      pending: this.queue.length
    };

    if (this.queue.length === 0) {
      this.log("info", "Semua baris dalam file Excel sudah berstatus 'SELESAI'.");
      this.setState("COMPLETED");
      return;
    }

    this.currentIndex = 0;
    this.setState("RUNNING");
    this.log("info", `Memulai otomasi dengan ${this.workerCount} Tab Worker paralel (Mode: ${this.authConfig.mode.toUpperCase()})...`);

    // Luncurkan tab worker
    for (let wId = 1; wId <= this.workerCount; wId++) {
      if (this.state !== "RUNNING") break;
      this.launchWorker(wId);
      await new Promise((r) => setTimeout(r, 600)); // Stagger antar peluncuran tab
    }
  },

  // 3. Loop Worker Tab
  async launchWorker(workerId) {
    this.log("info", `[Worker-${workerId}] Menginisialisasi tab worker...`);

    // Buat atau gunakan tab aktif
    let tab = null;
    try {
      const existingTabs = await chrome.tabs.query({ url: "*://fasih-sm.bps.go.id/*" });
      const usedTabIds = Object.values(this.activeWorkers).map(w => w.tabId);
      const availableTab = existingTabs.find(t => !usedTabIds.includes(t.id));

      if (availableTab && workerId === 1) {
        tab = availableTab;
        this.log("info", `[Worker-${workerId}] Menggunakan tab FASIH yang sudah terbuka (Tab ID: ${tab.id}).`);
      } else {
        tab = await chrome.tabs.create({ url: "https://fasih-sm.bps.go.id/app", active: false });
      }
    } catch (e) {
      tab = await chrome.tabs.create({ url: "https://fasih-sm.bps.go.id/app", active: false });
    }

    this.activeWorkers[workerId] = { tabId: tab.id, currentRow: null };

    // Loop pemrosesan baris untuk worker ini
    while (this.state === "RUNNING" || this.state === "PAUSED") {
      if (this.state === "PAUSED") {
        await new Promise((r) => setTimeout(r, 1000));
        continue;
      }

      if (this.state === "STOPPING" || this.state === "IDLE") {
        break;
      }

      // Ambil baris berikutnya dari antrean
      if (this.currentIndex >= this.queue.length) {
        this.log("info", `[Worker-${workerId}] Antrean tugas selesai.`);
        break;
      }

      const row = this.queue[this.currentIndex++];
      this.activeWorkers[workerId].currentRow = row;

      this.log("info", `[Worker-${workerId}] Memproses Baris Excel #${row._rowIndex} (Assignment: ${row.assignment_id || "-"})`);
      if (this.onRowUpdate) this.onRowUpdate(row._rowIndex, "PROSES", "Sedang diproses...");

      // Eksekusi baris di tab worker
      let resultStatus = "GAGAL";
      let resultKet = "";

      try {
        await this.navigateTabAndWaitReady(tab.id, row.url);

        // Kirim perintah eksekusi ke content script
        const response = await chrome.tabs.sendMessage(tab.id, {
          type: "EXECUTE_ASSIGNMENT",
          payload: {
            module: this.moduleId,
            row: row,
            options: { debugReview: this.debugReview },
            workerId: workerId
          }
        });

        if (response && response.success) {
          resultStatus = "SELESAI";
          resultKet = response.result.keterangan || "Berhasil Disubmit";
          this.stats.done++;
        } else {
          resultStatus = "GAGAL";
          resultKet = (response && response.error) || "Terjadi kesalahan pada formulir";
          this.stats.error++;
        }
      } catch (err) {
        resultStatus = "GAGAL";
        resultKet = err.message || "Timeout / Tab error";
        this.stats.error++;
        this.log("error", `[Worker-${workerId}] Error pada baris #${row._rowIndex}: ${resultKet}`);

        // Jika terindikasi sesi login habis
        if (resultKet.toLowerCase().includes("sesi") || resultKet.toLowerCase().includes("login")) {
          if (this.authConfig.mode === "manual") {
            this.pause();
            alert(`Sesi Login Habis:\n${resultKet}\nSilakan login kembali di browser.`);
          }
        }
      }

      this.stats.pending = Math.max(0, this.stats.total - this.stats.done - this.stats.error);

      // Perbarui hasil di ExcelIO
      window.ExcelIO.updateRowResult(row._rowIndex, resultStatus, resultKet);
      if (this.onRowUpdate) this.onRowUpdate(row._rowIndex, resultStatus, resultKet);
      if (this.onProgress) this.onProgress(this.stats);

      // Simpan checkpoint ke storage lokal browser
      chrome.storage.local.set({
        fasih_last_checkpoint: {
          timestamp: Date.now(),
          stats: this.stats,
          lastRow: row._rowIndex
        }
      });

      // Stagger delay antar assignment agar manusiawi
      await new Promise((r) => setTimeout(r, 1200 + Math.random() * 1500));
    }

    // Bersihkan worker
    delete this.activeWorkers[workerId];

    // Jika seluruh worker sudah selesai
    if (Object.keys(this.activeWorkers).length === 0) {
      if (this.state === "RUNNING") {
        this.setState("COMPLETED");
        this.log("info", `🏁 Seluruh antrean otomasi selesai! Berhasil: ${this.stats.done}, Gagal: ${this.stats.error}`);
        alert(`Otomasi Selesai!\n- Berhasil: ${this.stats.done}\n- Gagal: ${this.stats.error}`);
      }
    }
  },

  // 4. Navigasikan Tab, Tunggu DOM & Validasi Sesi Autentikasi
  async navigateTabAndWaitReady(tabId, targetUrl) {
    if (!targetUrl || !targetUrl.startsWith("http")) {
      throw new Error(`URL target tidak valid: '${targetUrl}'`);
    }

    await chrome.tabs.update(tabId, { url: targetUrl });

    // Tunggu tab berstatus 'complete'
    await new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        chrome.tabs.onUpdated.removeListener(listener);
        reject(new Error("Timeout navigasi ke URL assignment"));
      }, 35000);

      function listener(updatedTabId, changeInfo) {
        if (updatedTabId === tabId && changeInfo.status === "complete") {
          clearTimeout(timeoutId);
          chrome.tabs.onUpdated.removeListener(listener);
          resolve();
        }
      }

      chrome.tabs.onUpdated.addListener(listener);
    });

    // Jeda sejenak untuk rendering React & inisialisasi content script
    await new Promise((r) => setTimeout(r, 1200));

    // Handshake PING ke content script
    let ready = false;
    for (let attempts = 0; attempts < 6; attempts++) {
      try {
        const res = await chrome.tabs.sendMessage(tabId, { type: "PING_TAB" });
        if (res && res.status === "READY") {
          ready = true;
          break;
        }
      } catch (e) {
        await new Promise((r) => setTimeout(r, 600));
      }
    }

    // Jika belum respons, coba injeksikan content script secara eksplisit
    if (!ready) {
      try {
        this.log("info", "Menginjeksi ulang content script ke tab worker...");
        await chrome.scripting.executeScript({
          target: { tabId },
          files: [
            "content/fh_namespace.js",
            "content/dom_toolkit.js",
            "content/session_guard.js",
            "content/tasks/remark_kbli.task.js",
            "content/tasks/kbli_sembako.task.js",
            "content/tasks/kbli_pmm.task.js",
            "content/tasks/cleaning_usaha.task.js",
            "content/tasks/cleaning_nik_r30.task.js",
            "content/tasks/cleaning_nik_r27.task.js",
            "content/content_main.js"
          ]
        });
        await new Promise((r) => setTimeout(r, 600));
        const res = await chrome.tabs.sendMessage(tabId, { type: "PING_TAB" });
        if (res && res.status === "READY") {
          ready = true;
        }
      } catch (scriptErr) {
        this.log("warn", `Injeksi skrip fallback: ${scriptErr.message}`);
      }
    }

    if (!ready) {
      throw new Error("Content script pada tab belum siap setelah navigasi");
    }

    // 5. Pemeriksaan Sesi Autentikasi Tab
    const authStatus = await this.checkTabAuth(tabId);
    if (!authStatus.active) {
      this.log("warn", `[Auth Guard] Sesi login tidak aktif di tab (${authStatus.reason})`);

      // Jika Auto-Login aktif dan kredensial tersedia -> jalankan Auto-Login sekarang
      if (this.authConfig.mode === "auto" && this.authConfig.username && this.authConfig.password) {
        this.log("info", `[Auth Manager] Melakukan Auto-Login SSO BPS untuk akun '${this.authConfig.username}'...`);
        await this.performAutoLoginOnTab(tabId);
        this.log("info", "[Auth Manager] Auto-Login berhasil. Membuka kembali URL target...");
        await this.navigateTabAndWaitReady(tabId, targetUrl);
        return;
      } else {
        throw new Error("Sesi SSO BPS belum aktif atau telah kedaluwarsa. Silakan lakukan login SSO di tab peramban terlebih dahulu.");
      }
    }
  },

  // 5. Helper Cek Status Sesi Tab
  async checkTabAuth(tabId) {
    try {
      const res = await chrome.tabs.sendMessage(tabId, { type: "CHECK_AUTH_STATUS" });
      if (res && res.success && res.auth) {
        return res.auth;
      }
    } catch (e) {}
    return { active: false, status: "UNKNOWN", reason: "Tab belum merespon status auth" };
  },

  // 6. Helper Eksekusi Auto-Login pada Tab
  async performAutoLoginOnTab(tabId) {
    const res = await chrome.tabs.sendMessage(tabId, {
      type: "PERFORM_AUTO_LOGIN",
      payload: {
        username: this.authConfig.username,
        password: this.authConfig.password
      }
    });

    if (!res || !res.success) {
      throw new Error(res?.error || "Gagal melakukan Auto-Login SSO");
    }
    return res;
  },

  // 7. Kontrol Jeda, Lanjut & Berhenti
  pause() {
    if (this.state === "RUNNING") {
      this.setState("PAUSED");
      this.log("warn", "Otomasi dijeda oleh pengguna.");
    }
  },

  resume() {
    if (this.state === "PAUSED") {
      this.setState("RUNNING");
      this.log("info", "Melanjutkan otomasi...");
    }
  },

  stop() {
    this.setState("STOPPING");
    this.log("warn", "Menghentikan seluruh worker otomasi...");

    for (const [wId, wData] of Object.entries(this.activeWorkers)) {
      if (wData.tabId) {
        chrome.tabs.sendMessage(wData.tabId, { type: "STOP_EXECUTION" }).catch(() => {});
      }
    }

    setTimeout(() => {
      this.setState("IDLE");
      this.log("info", "Otomasi berhasil dihentikan secara aman.");
    }, 1000);
  }
};
