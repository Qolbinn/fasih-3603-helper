// ==============================================================================
// FASIH 3603 HELPER - BACKGROUND SERVICE WORKER (MANIFEST V3)
// ==============================================================================

// Buka Side Panel secara otomatis saat user mengklik ikon ekstensi di toolbar
chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.warn("[FASIH 3603] Gagal mengatur panel behavior:", error));

// Event listener saat ekstensi baru dipasang atau diperbarui
chrome.runtime.onInstalled.addListener((details) => {
  console.log("[FASIH 3603 Helper] Ekstensi berhasil diinstal/diperbarui:", details.reason);
});

// Listener pesan komunikasi background (jika ada kebutuhan relay antar tab/sidepanel)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "PING_BACKGROUND") {
    sendResponse({ status: "OK", timestamp: Date.now() });
    return true;
  }
  
  if (message.type === "OPEN_SIDEPANEL" && sender.tab?.windowId) {
    chrome.sidePanel.open({ windowId: sender.tab.windowId }).catch((err) => {
      console.warn("[FASIH 3603] Gagal membuka side panel:", err);
    });
    sendResponse({ status: "REQUESTED" });
    return true;
  }
});
