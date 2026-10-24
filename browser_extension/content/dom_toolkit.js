// ==============================================================================
// FASIH 3603 HELPER - DOM TOOLKIT (NATIVE PLAYWRIGHT EQUIVALENT)
// ==============================================================================

(function () {
  const FH = window.FH;

  // 1. Jitter & Sleep Timers
  FH.sleep = function (ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  };

  FH.randomSleep = async function (minSec = 0.5, maxSec = 1.2, allowHesitation = true) {
    if (FH.state.shouldStop) return;
    let sec = minSec + Math.random() * (maxSec - minSec);
    if (allowHesitation && Math.random() < 0.15) {
      sec += 0.4 + Math.random() * 0.8;
    }
    await FH.sleep(sec * 1000);
  };

  FH.jitter = async function (minSec = 0.1, maxSec = 0.25) {
    if (FH.state.shouldStop) return;
    const sec = minSec + Math.random() * (maxSec - minSec);
    await FH.sleep(sec * 1000);
  };

  FH.shouldStop = function () {
    return FH.state.shouldStop;
  };

  // 2. Selectors Helpers (XPath, find, findAll & byText)
  FH.byXPath = function (xpath, root = document) {
    try {
      const result = document.evaluate(
        xpath,
        root,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null
      );
      return result.singleNodeValue;
    } catch (e) {
      return null;
    }
  };

  FH.allByXPath = function (xpath, root = document) {
    const list = [];
    try {
      const result = document.evaluate(
        xpath,
        root,
        null,
        XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
        null
      );
      for (let i = 0; i < result.snapshotLength; i++) {
        list.push(result.snapshotItem(i));
      }
    } catch (e) {}
    return list;
  };

  FH.find = function (selector, root = document) {
    if (!selector) return null;
    if (typeof selector === "function") return selector();
    if (selector.startsWith("xpath=")) {
      return FH.byXPath(selector.replace("xpath=", ""), root);
    }

    // Split comma-separated selector groups safely
    const parts = selector.split(/,(?![^()]*\))/).map((s) => s.trim()).filter(Boolean);

    for (const part of parts) {
      if (part.startsWith("xpath=")) {
        const found = FH.byXPath(part.replace("xpath=", ""), root);
        if (found) return found;
        continue;
      }

      // Check if selector part contains :has-text(...)
      const match = part.match(/^(.*?):has-text\((['"]?)(.*?)\2\)(.*)$/);
      if (match) {
        const base = match[1].trim() || "*";
        const searchText = match[3].toLowerCase();
        const trailer = match[4].trim();

        let candidates = [];
        try {
          candidates = Array.from(root.querySelectorAll(base));
        } catch (e) {
          candidates = [];
        }

        for (const cand of candidates) {
          const text = (cand.textContent || "").toLowerCase();
          if (text.includes(searchText)) {
            if (trailer) {
              const sub = FH.find(trailer, cand);
              if (sub) return sub;
            } else {
              return cand;
            }
          }
        }
      } else {
        try {
          const found = root.querySelector(part);
          if (found) return found;
        } catch (e) {}
      }
    }
    return null;
  };

  FH.findAll = function (selector, root = document) {
    if (!selector) return [];
    if (selector.startsWith("xpath=")) {
      return FH.allByXPath(selector.replace("xpath=", ""), root);
    }

    const results = [];
    const parts = selector.split(/,(?![^()]*\))/).map((s) => s.trim()).filter(Boolean);

    for (const part of parts) {
      if (part.startsWith("xpath=")) {
        results.push(...FH.allByXPath(part.replace("xpath=", ""), root));
        continue;
      }

      const match = part.match(/^(.*?):has-text\((['"]?)(.*?)\2\)(.*)$/);
      if (match) {
        const base = match[1].trim() || "*";
        const searchText = match[3].toLowerCase();
        const trailer = match[4].trim();

        let candidates = [];
        try {
          candidates = Array.from(root.querySelectorAll(base));
        } catch (e) {
          candidates = [];
        }

        for (const cand of candidates) {
          const text = (cand.textContent || "").toLowerCase();
          if (text.includes(searchText)) {
            if (trailer) {
              const subs = FH.findAll(trailer, cand);
              results.push(...subs);
            } else {
              results.push(cand);
            }
          }
        }
      } else {
        try {
          const list = root.querySelectorAll(part);
          results.push(...Array.from(list));
        } catch (e) {}
      }
    }
    return results;
  };

  FH.byText = function (selector, text, root = document) {
    const elements = root.querySelectorAll(selector);
    const lowerText = text.toLowerCase().trim();
    for (const el of elements) {
      if (el.textContent && el.textContent.toLowerCase().includes(lowerText)) {
        return el;
      }
    }
    return null;
  };

  FH.allByText = function (selector, text, root = document) {
    const elements = root.querySelectorAll(selector);
    const lowerText = text.toLowerCase().trim();
    const matches = [];
    for (const el of elements) {
      if (el.textContent && el.textContent.toLowerCase().includes(lowerText)) {
        matches.push(el);
      }
    }
    return matches;
  };

  // 3. Visibility Checker
  FH.isVisible = function (el) {
    if (!el) return false;
    if (el.nodeType !== Node.ELEMENT_NODE) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") {
      return false;
    }
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  // 4. Element Waiter (MutationObserver + Polling)
  FH.waitFor = function (selectorOrFn, options = {}) {
    const { timeout = 20000, state = "visible", root = document } = options;
    const startTime = Date.now();

    return new Promise((resolve, reject) => {
      function check() {
        if (FH.state.shouldStop) {
          return reject(new Error("Pemberhentian otomasi diminta oleh pengguna"));
        }

        let target = null;
        if (typeof selectorOrFn === "function") {
          target = selectorOrFn();
        } else {
          target = FH.find(selectorOrFn, root);
        }

        if (state === "attached" && target) {
          cleanup();
          return resolve(target);
        }

        const visible = target ? FH.isVisible(target) : false;

        if (state === "visible" && visible) {
          cleanup();
          return resolve(target);
        }

        if (state === "hidden" && (!target || !visible)) {
          cleanup();
          return resolve(true);
        }

        if (Date.now() - startTime > timeout) {
          cleanup();
          return reject(
            new Error(`Timeout (${timeout}ms) menunggu elemen '${selectorOrFn}' dengan state '${state}'`)
          );
        }
      }

      const observer = new MutationObserver(check);
      observer.observe(document.body, { childList: true, subtree: true, attributes: true });

      const intervalId = setInterval(check, 200);

      function cleanup() {
        observer.disconnect();
        clearInterval(intervalId);
      }

      check();
    });
  };

  // 5. Human-like Click Simulation
  FH.humanClick = async function (elOrSelector, options = {}) {
    if (FH.state.shouldStop) return;
    const { force = false, timeout = 15000, root = document } = options;

    let el = elOrSelector;
    if (typeof elOrSelector === "string") {
      el = await FH.waitFor(elOrSelector, { timeout, root });
    }

    if (!el) throw new Error(`Elemen untuk klik tidak ditemukan: ${elOrSelector}`);

    try {
      el.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
    } catch (e) {}

    await FH.jitter(0.1, 0.25);

    const rect = el.getBoundingClientRect();
    const clientX = rect.left + rect.width / 2 + (Math.random() * 4 - 2);
    const clientY = rect.top + rect.height / 2 + (Math.random() * 4 - 2);

    const mouseEvents = ["pointerover", "mouseover", "pointerdown", "mousedown", "pointerup", "mouseup", "click"];

    for (const evtName of mouseEvents) {
      const evt = new MouseEvent(evtName, {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX,
        clientY,
        buttons: evtName.includes("down") ? 1 : 0
      });
      el.dispatchEvent(evt);
    }

    if (typeof el.focus === "function") {
      el.focus();
    }

    if (force && typeof el.click === "function") {
      el.click();
    }
  };

  // 6. Human-like Input Typing (React Synthetic Events Compatible)
  FH.typeText = async function (inputOrSelector, text, options = {}) {
    if (FH.state.shouldStop) return;
    const { delayMs = 30, clearFirst = true, root = document } = options;

    let input = inputOrSelector;
    if (typeof inputOrSelector === "string") {
      input = await FH.waitFor(inputOrSelector, { timeout: 15000, root });
    }

    if (!input) throw new Error(`Input untuk pengetikan tidak ditemukan: ${inputOrSelector}`);

    await FH.humanClick(input);
    input.focus();

    const isInput = input instanceof HTMLInputElement;
    const isTextArea = input instanceof HTMLTextAreaElement;
    const prototype = isInput
      ? window.HTMLInputElement.prototype
      : isTextArea
      ? window.HTMLTextAreaElement.prototype
      : null;

    const nativeSetter = prototype
      ? Object.getOwnPropertyDescriptor(prototype, "value").set
      : null;

    if (clearFirst) {
      if (nativeSetter) {
        nativeSetter.call(input, "");
      } else {
        input.value = "";
      }
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      await FH.sleep(50);
    }

    const str = String(text);
    let currentVal = clearFirst ? "" : input.value;

    for (let i = 0; i < str.length; i++) {
      if (FH.state.shouldStop) return;
      const char = str[i];
      currentVal += char;

      if (nativeSetter) {
        nativeSetter.call(input, currentVal);
      } else {
        input.value = currentVal;
      }

      input.dispatchEvent(new InputEvent("input", { bubbles: true, cancelable: true, data: char }));
      await FH.sleep(delayMs + Math.random() * 20);
    }

    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
    await FH.jitter(0.1, 0.2);
  };

  // 7. Key Press Helper
  FH.pressKey = function (element, key, code) {
    const target = element || document.activeElement || document.body;
    const opts = { key, code: code || key, bubbles: true, cancelable: true };
    target.dispatchEvent(new KeyboardEvent("keydown", opts));
    target.dispatchEvent(new KeyboardEvent("keypress", opts));
    target.dispatchEvent(new KeyboardEvent("keyup", opts));
  };

  // 8. Add Remarks (Catatan) to Element (Port 100% dari Python)
  FH.addRemark = async function (containerOrSelector, noteText) {
    if (FH.state.shouldStop) return;

    let container = containerOrSelector;
    if (typeof containerOrSelector === "string") {
      container = await FH.waitFor(containerOrSelector, { state: "attached", timeout: 30000 });
    }

    if (!container) throw new Error(`Container elemen untuk Catatan tidak ditemukan: ${containerOrSelector}`);

    try {
      container.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (e) {}
    await FH.randomSleep(0.4, 0.7);

    // Cari tombol Catatan yang visible di dalam container
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
      throw new Error(`Tombol Catatan visible tidak ditemukan pada container (${containerOrSelector})`);
    }

    await FH.humanClick(btnCatatan);
    await FH.randomSleep(0.7, 1.1);

    // Tunggu dialog pop-up modal Catatan
    const dialog = await FH.waitFor("div[role='dialog']", { timeout: 25000 });
    const noteStr = String(noteText).trim();

    // Periksa apakah pesan catatan sudah pernah dikirim sebelumnya
    let alreadyExists = false;
    const bubbles = dialog.querySelectorAll("div[class*='whitespace-pre-wrap'], div[class*='wrap-break-word'], div[class*='break-words']");
    for (const b of bubbles) {
      if (b.textContent && b.textContent.trim() === noteStr) {
        alreadyExists = true;
        break;
      }
    }

    if (alreadyExists) {
      FH.log("info", `Catatan '${noteStr}' sudah tercatat sebelumnya. Melewati pengiriman ulang.`);
    } else {
      const textarea = await FH.waitFor(() => dialog.querySelector("textarea[placeholder*='Tambah catatan'], textarea"), { timeout: 25000 });
      await FH.typeText(textarea, noteStr, { delayMs: 25 });
      await FH.jitter(0.15, 0.25);

      const btnSimpan = await FH.waitFor(() => FH.find("button[title='Simpan'], button:has-text('Simpan')", dialog) || FH.byText("button", "Simpan", dialog), { timeout: 20000 });
      await FH.humanClick(btnSimpan);
      await FH.randomSleep(0.8, 1.2);
    }

    // Tutup dialog modal Catatan
    const btnClose = FH.find("button[aria-label='Dismiss'], button[title='Tutup'], button:has-text('Tutup')", dialog) || FH.byText("button", "Tutup", dialog);
    if (btnClose && FH.isVisible(btnClose)) {
      await FH.humanClick(btnClose);
    } else {
      FH.pressKey(document.body, "Escape", "Escape");
    }

    await FH.waitFor("div[role='dialog']", { state: "hidden", timeout: 8000 }).catch(() => {
      FH.pressKey(document.body, "Escape", "Escape");
    });

    await FH.randomSleep(0.4, 0.7);
  };

  // 9. Dual Remark Helper to Master KBLI
  FH.addRemarksToMasterKBLIIfVisible = async function (noteText, masterSelector = "div[id^='kbli#'], div[id='kbli']") {
    try {
      const containerMaster = FH.find(masterSelector);
      if (containerMaster && FH.isVisible(containerMaster)) {
        FH.log("info", `Menambahkan catatan ganda '${noteText}' ke Master KBLI...`);
        await FH.addRemark(containerMaster, noteText);
        FH.log("info", `Catatan ganda '${noteText}' pada Master KBLI berhasil disimpan.`);
      }
    } catch (e) {
      FH.log("warn", `Peringatan remark Master KBLI (dilewati aman): ${e.message}`);
    }
  };

  // 10. Radio Selector Helper
  FH.selectRadioOption = async function (containerEl, optionText, optionValue = null) {
    if (!containerEl) throw new Error("Container radio tidak ditemukan");

    // Cari button radio option di dalam container
    let targetBtn = null;
    const buttons = containerEl.querySelectorAll("button[role='radio'], button[type='button'], div[role='radio']");

    for (const btn of buttons) {
      const txt = (btn.textContent || "").trim();
      const val = btn.getAttribute("value") || btn.getAttribute("data-value") || "";
      if ((optionValue && val === optionValue) || (optionText && txt.toLowerCase().includes(optionText.toLowerCase()))) {
        targetBtn = btn;
        break;
      }
    }

    if (!targetBtn) {
      const labels = containerEl.querySelectorAll("label");
      for (const lbl of labels) {
        if (lbl.textContent && lbl.textContent.toLowerCase().includes(optionText.toLowerCase())) {
          targetBtn = lbl;
          break;
        }
      }
    }

    if (!targetBtn) {
      throw new Error(`Opsi radio '${optionText || optionValue}' tidak ditemukan di container`);
    }

    await FH.humanClick(targetBtn);
    await FH.randomSleep(0.5, 0.8);
  };

  FH.isAnyRadioSelected = function (containerEl) {
    if (!containerEl) return false;
    const activeBtn = containerEl.querySelector(
      "button[aria-checked='true'], button[data-state='checked'], input[type='radio']:checked"
    );
    return !!activeBtn;
  };

  // 11. Anomali Switch Toggle Helper (Port 100% dari ensure_anomali_switch_active Python)
  FH.ensureAnomaliSwitchActive = async function (timeout = 35000) {
    FH.log("info", "Memeriksa status toggle 'Tampilkan Anomali Usaha dan Keluarga'...");

    // Tunggu container switch anomali muncul di Blok Catatan
    const box = await FH.waitFor("div#cek_anomali_button, [id='cek_anomali_button']", {
      timeout,
      state: "visible"
    });

    try {
      box.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (e) {}
    await FH.randomSleep(0.3, 0.6);

    const swInput = box.querySelector("input[role='switch']");
    const swControl = box.querySelector("[id^='switch-'][id$='-control'], span[class*='switch-thumb'], div[role='switch']");

    function isActive() {
      if (!swInput) return true;
      return swInput.getAttribute("aria-checked") === "true" || swInput.checked;
    }

    if (isActive()) {
      FH.log("info", "Toggle 'Tampilkan Anomali Usaha dan Keluarga' sudah aktif -> Dibiarkan.");
      return true;
    }

    FH.log("info", "Toggle belum aktif -> Mengaktifkan switch anomali...");
    for (let attempt = 1; attempt <= 3; attempt++) {
      const targetClick = swControl || swInput;
      if (targetClick) {
        await FH.humanClick(targetClick);
      }

      for (let j = 0; j < 10; j++) {
        await FH.sleep(300);
        if (isActive()) {
          FH.log("info", "Toggle 'Tampilkan Anomali Usaha dan Keluarga' berhasil diaktifkan.");
          return true;
        }
      }
      FH.log("warn", `Switch anomali belum aktif setelah klik (percobaan ${attempt}/3). Mengulang...`);
    }

    throw new Error("Gagal mengaktifkan toggle Tampilkan Anomali Usaha dan Keluarga.");
  };

  // 12. Currency Formatting & Input Helpers
  FH.parseFasihCurrency = function (valStr) {
    if (!valStr) return 0;
    const cleaned = String(valStr).replace(/[^\d]/g, "");
    return cleaned ? parseInt(cleaned, 10) : 0;
  };

  FH.safeFillCurrency = async function (containerOrSelector, value) {
    const valInt = Math.round(Number(value) || 0);
    const valStr = String(valInt);

    let container = containerOrSelector;
    if (typeof containerOrSelector === "string") {
      container = await FH.waitFor(containerOrSelector, { timeout: 15000 });
    }
    if (!container) throw new Error(`Container input nominal tidak ditemukan: ${containerOrSelector}`);

    try {
      container.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (e) {}

    const input = container.querySelector("input[type='text'], input");
    if (!input) throw new Error("Input teks tidak ditemukan di dalam container");

    await FH.typeText(input, valStr, { delayMs: 25, clearFirst: true });
    FH.pressKey(input, "Tab", "Tab");
    await FH.randomSleep(0.3, 0.5);
  };
})();
