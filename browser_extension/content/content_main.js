// ==============================================================================
// FASIH 3603 HELPER - CONTENT SCRIPT MAIN DISPATCHER
// ==============================================================================

(function () {
  const FH = window.FH;

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    // 1. Handshake PING
    if (message.type === "PING_TAB") {
      const sess = FH.checkSessionActive ? FH.checkSessionActive() : { active: true };
      sendResponse({
        status: "READY",
        url: window.location.href,
        sessionActive: sess.active,
        authStatus: sess.status
      });
      return true;
    }

    // 2. Pemeriksaan Status Autentikasi
    if (message.type === "CHECK_AUTH_STATUS") {
      const sess = FH.checkSessionActive ? FH.checkSessionActive() : { active: true, status: "UNKNOWN" };
      sendResponse({
        success: true,
        auth: sess,
        url: window.location.href
      });
      return true;
    }

    // 3. Eksekusi Auto-Login SSO BPS
    if (message.type === "PERFORM_AUTO_LOGIN") {
      const { username, password } = message.payload || {};
      FH.performAutoLogin(username, password)
        .then((res) => sendResponse({ success: true, result: res }))
        .catch((err) => sendResponse({ success: false, error: err.message }));
      return true;
    }

    // 4. Perintah Hentikan Otomasi
    if (message.type === "STOP_EXECUTION") {
      FH.state.shouldStop = true;
      FH.state.isRunning = false;
      FH.log("warn", "Perintah penghentian otomasi diterima dari Side Panel.");
      sendResponse({ status: "STOPPED" });
      return true;
    }

    // 5. Eksekusi Baris Tugas Assignment
    if (message.type === "EXECUTE_ASSIGNMENT") {
      const { module, row, options = {}, workerId = 1 } = message.payload;
      FH.state.isRunning = true;
      FH.state.shouldStop = false;
      FH.state.activeWorkerId = workerId;
      FH.logs = [];

      FH.log("info", `[Worker-${workerId}] Menerima tugas modul '${module}'...`);

      const taskFn = FH.tasks[module];
      if (!taskFn) {
        const errMsg = `Modul task '${module}' belum didaftarkan di content script!`;
        FH.log("error", errMsg);
        sendResponse({ success: false, error: errMsg, logs: FH.logs });
        return true;
      }

      // Jalankan task
      taskFn(row, options)
        .then((result) => {
          FH.state.isRunning = false;
          sendResponse({
            success: true,
            result: result || { status: "SELESAI", keterangan: "Selesai" },
            logs: FH.logs
          });
        })
        .catch((err) => {
          FH.state.isRunning = false;
          FH.log("error", `Gagal memproses baris: ${err.message}`);
          sendResponse({
            success: false,
            error: err.message,
            logs: FH.logs
          });
        });

      return true;
    }
  });

  console.log("[FASIH 3603 Helper] Content script aktif dan siap di:", window.location.href);
})();
