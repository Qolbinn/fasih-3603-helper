// ==============================================================================
// FASIH 3603 HELPER - SESSION & AUTH GUARD (SSO BPS AUTO / MANUAL MANAGER)
// Paritas 100% dengan core/browser_manager.py
// ==============================================================================

(function () {
  const FH = window.FH;

  // 1. Cek Status Login Halaman
  FH.checkSessionActive = function () {
    const currentUrl = (window.location.href || "").toLowerCase().trim();
    if (!currentUrl || currentUrl === "about:blank") {
      return { active: false, status: "NO_PAGE", reason: "Halaman kosong" };
    }

    // 1. Domain SSO Keycloak
    if (currentUrl.includes("sso.bps.go.id") || currentUrl.includes("/realms/") || currentUrl.includes("oauth2")) {
      return { active: false, status: "SSO_PAGE", reason: "Halaman login SSO BPS aktif" };
    }

    // 2. Path login Fasih
    const pathname = window.location.pathname.toLowerCase().replace(/\/+$/, "");
    if (pathname.includes("/auth/login") || pathname.endsWith("/login")) {
      return { active: false, status: "FASIH_LOGIN_PAGE", reason: "Halaman login Fasih aktif" };
    }

    // 3. Elemen login di DOM
    const loginIndicators = [
      "a:has-text('Lanjutkan dengan SSO')",
      "button:has-text('Lanjutkan dengan SSO')",
      "span:has-text('Lanjutkan dengan SSO')",
      "h1:has-text('Selamat Datang Kembali')",
      "dd:has-text('Masuk ke akun Anda')",
      "#kc-form-login",
      "#kc-login",
      "#username"
    ];

    for (const sel of loginIndicators) {
      const el = FH.find(sel);
      if (el && FH.isVisible(el)) {
        return { active: false, status: "NOT_LOGGED_IN", reason: "Form login SSO BPS terdeteksi di halaman" };
      }
    }

    // 4. Indikator autentikasi eksplisit Fasih
    const authIndicators = [
      ".fasih-form-sidebar",
      "a[href*='logout']",
      "button:has-text('Logout')",
      "button:has-text('Keluar')",
      "a:has-text('Survei')",
      "a:has-text('Penugasan')",
      "#btn-kirim",
      "div[title*='BLOK']"
    ];

    for (const sel of authIndicators) {
      const el = FH.find(sel);
      if (el && FH.isVisible(el)) {
        return { active: true, status: "LOGGED_IN", reason: "Sesi login Fasih aktif" };
      }
    }

    // Jika pada path aplikasi (/app, /assignment, /surveys, dll.) tanpa form login
    if (
      pathname.includes("/assignment") ||
      pathname.includes("/survey") ||
      pathname.includes("/monitoring") ||
      pathname.includes("/app")
    ) {
      return { active: true, status: "LOGGED_IN", reason: "Berada pada rute internal Fasih" };
    }

    return { active: false, status: "UNKNOWN", reason: "Sesi belum terkonfirmasi aktif" };
  };

  // 2. Eksekusi Auto-Login SSO BPS (Diadaptasi 1:1 dari BrowserManager.perform_auto_login)
  FH.performAutoLogin = async function (username, password) {
    if (!username || !password) {
      throw new Error("Username atau Password SSO BPS kosong!");
    }

    FH.log("info", "Memulai proses Auto-Login SSO BPS...");

    // A. Jika di halaman Fasih dan ada tombol 'Lanjutkan dengan SSO'
    const loginBtnSelectors = [
      "a:has-text('Lanjutkan dengan SSO')",
      "button:has-text('Lanjutkan dengan SSO')",
      "span:has-text('Lanjutkan dengan SSO')",
      "a[href*='oauth2']",
      "a[href*='/auth/login']",
      "button:has-text('Masuk')"
    ];

    for (const sel of loginBtnSelectors) {
      const btn = FH.find(sel);
      if (btn && FH.isVisible(btn)) {
        FH.log("info", "Mengeklik tombol 'Lanjutkan dengan SSO'...");
        await FH.humanClick(btn);
        await FH.randomSleep(1.0, 1.8);
        break;
      }
    }

    // B. Tunggu form input SSO (#username)
    FH.log("info", "Menunggu form login SSO BPS (#username)...");
    const userInput = await FH.waitFor("#username, input[name='username']", { timeout: 25000 });
    await FH.randomSleep(0.4, 0.7);

    // C. Ketikkan Username & Password
    FH.log("info", `Mengisikan username SSO '${username}'...`);
    await FH.typeText(userInput, username, { delayMs: 25 });
    await FH.jitter(0.1, 0.2);

    const passInput = await FH.waitFor("#password, input[name='password']", { timeout: 15000 });
    FH.log("info", "Mengisikan password SSO...");
    await FH.typeText(passInput, password, { delayMs: 25 });
    await FH.randomSleep(0.3, 0.6);

    // D. Kirim Form Login
    FH.log("info", "Mengirim kredensial SSO...");
    const submitBtn = FH.find("#kc-login, button[type='submit'], input[type='submit']");
    if (submitBtn && FH.isVisible(submitBtn)) {
      await FH.humanClick(submitBtn);
    } else {
      FH.pressKey(passInput, "Enter", "Enter");
    }

    await FH.sleep(2000);

    // E. Periksa pesan error kredensial salah
    const errorElem = FH.find(".alert-error, #input-error, .kc-feedback-text, span.kc-feedback-text");
    if (errorElem && FH.isVisible(errorElem)) {
      const errText = (errorElem.textContent || "").trim();
      throw new Error(`Login ditolak oleh SSO BPS: '${errText}'`);
    }

    // F. Periksa apakah akun membutuhkan kode OTP
    const otpElem = FH.find("#otp, input[name='otp']");
    if (otpElem && FH.isVisible(otpElem)) {
      throw new Error("Akun memerlukan kode OTP. Fitur Auto-Login khusus akun non-OTP, silakan gunakan mode Login Manual.");
    }

    // G. Tunggu redirect kembali ke domain Fasih dan verifikasi sesi aktif
    FH.log("info", "Menunggu pengalihan kembali ke portal Fasih...");
    const startTime = Date.now();
    while (Date.now() - startTime < 30000) {
      await FH.sleep(1000);
      const sess = FH.checkSessionActive();
      if (sess.active && sess.status === "LOGGED_IN") {
        FH.log("info", "✨ Auto-Login SSO BPS berhasil diselesaikan!");
        return { success: true, message: "Berhasil login ke Fasih BPS" };
      }
    }

    throw new Error("Timeout menunggu pengalihan ke portal Fasih setelah submit SSO.");
  };

  // Monitor periodik saat otomasi aktif
  setInterval(() => {
    if (FH.state.isRunning) {
      const sess = FH.checkSessionActive();
      if (!sess.active) {
        FH.log("error", `[Auth Guard] ${sess.reason}! Menangguhkan tugas...`);
        try {
          chrome.runtime.sendMessage({
            type: "SESSION_EXPIRED",
            payload: { reason: sess.reason, url: window.location.href, status: sess.status }
          }).catch(() => {});
        } catch (e) {}
      }
    }
  }, 3000);
})();
