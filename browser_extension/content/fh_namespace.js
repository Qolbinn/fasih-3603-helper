// ==============================================================================
// FASIH 3603 HELPER - CONTENT SCRIPT GLOBAL NAMESPACE
// ==============================================================================

window.FH = window.FH || {};

// Objek penampung status & modul task
window.FH.tasks = window.FH.tasks || {};
window.FH.state = {
  isRunning: false,
  isPaused: false,
  shouldStop: false,
  currentAssignmentId: null,
  activeWorkerId: null
};

// Logging helper ke side panel & console
window.FH.logs = [];

window.FH.log = function (level, message) {
  const timestamp = new Date().toLocaleTimeString("id-ID", { hour12: false });
  const entry = { timestamp, level, message };
  window.FH.logs.push(entry);

  const prefix = `[FH-${level.toUpperCase()}]`;
  if (level === "error") {
    console.error(prefix, message);
  } else if (level === "warn") {
    console.warn(prefix, message);
  } else {
    console.log(prefix, message);
  }

  // Kirim log secara real-time ke Side Panel
  try {
    chrome.runtime.sendMessage({
      type: "LOG_STREAM",
      payload: entry
    }).catch(() => {});
  } catch (e) {
    // Abaikan jika listener side panel tertutup
  }
};
