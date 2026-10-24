import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright
from core.browser_manager import BrowserManager
from modules.remark_kbli.engine import _add_remarks_to_master_kbli_if_visible as remark_kbli_helper
from modules.kbli_sembako.engine import _add_remarks_to_master_kbli_if_visible as sembako_helper
from modules.kbli_pmm.engine import _add_remarks_to_master_kbli_if_visible as pmm_helper

HTML_TEST = """
<!DOCTYPE html>
<html>
<head><title>Test Dual Remarks</title></head>
<body>
  <!-- Container Master KBLI Visible -->
  <div id="kbli#1001" style="display: block;">
    <button type="button" title="Catatan" aria-label="Catatan" id="btn-catatan-master">Catatan</button>
  </div>

  <!-- Container Master KBLI Hidden -->
  <div id="kbli#hidden" style="display: none;">
    <button type="button" title="Catatan" aria-label="Catatan">Catatan</button>
  </div>

  <!-- Modal Dialog Catatan Mock -->
  <div role="dialog" style="display: none;" id="dialog-mock">
    <div id="bubble-list"></div>
    <textarea placeholder="Tambah catatan..."></textarea>
    <button type="button" title="Simpan" id="btn-simpan">Simpan</button>
    <button type="button" title="Tutup" id="btn-tutup">Tutup</button>
  </div>

  <script>
    const dialog = document.getElementById('dialog-mock');
    const bubbleList = document.getElementById('bubble-list');
    const textarea = dialog.querySelector('textarea');
    const btnSimpan = document.getElementById('btn-simpan');
    const btnTutup = document.getElementById('btn-tutup');

    document.querySelectorAll("button[title='Catatan']").forEach(btn => {
      btn.addEventListener('click', () => {
        dialog.style.display = 'block';
      });
    });

    btnSimpan.addEventListener('click', () => {
      const val = textarea.value.trim();
      if (val) {
        const b = document.createElement('div');
        b.className = 'whitespace-pre-wrap';
        b.innerText = val;
        bubbleList.appendChild(b);
        textarea.value = '';
      }
      dialog.style.display = 'none';
    });

    btnTutup.addEventListener('click', () => {
      dialog.style.display = 'none';
    });
  </script>
</body>
</html>
"""

chrome_path = BrowserManager.get_installed_browser_path()
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=chrome_path, headless=True)
    page = browser.new_page()
    page.set_content(HTML_TEST)

    # 1. Test remark_kbli helper saat master_kbli visible
    print("Testing 1: remark_kbli_helper pada container visible...")
    res1 = remark_kbli_helper(page, "#0", "div[id^='kbli#1001']", worker_prefix="[TEST] ")
    assert res1 is True
    bubble_text = page.locator("#bubble-list .whitespace-pre-wrap").first.inner_text()
    assert bubble_text == "#0"
    print("   Test 1 PASSED: Remark #0 berhasil disimpan ke master kbli!")

    # 2. Test kbli_sembako helper saat master_kbli visible (simpan #4)
    print("Testing 2: sembako_helper pada container visible...")
    res2 = sembako_helper(page, "#4", "div[id^='kbli#1001']", worker_prefix="[TEST] ")
    assert res2 is True
    print("   Test 2 PASSED: Remark #4 berhasil disimpan ke master kbli!")

    # 3. Test pmm_helper saat master_kbli hidden
    print("Testing 3: pmm_helper pada container hidden...")
    res3 = pmm_helper(page, "#0", "div[id^='kbli#hidden']", worker_prefix="[TEST] ")
    assert res3 is False
    print("   Test 3 PASSED: Container hidden dilewati dengan aman!")

    # 4. Test saat selector sama sekali tidak ada di halaman
    print("Testing 4: helper pada container yang tidak ada...")
    res4 = pmm_helper(page, "#0", "div[id^='kbli#nonexistent']", worker_prefix="[TEST] ")
    assert res4 is False
    print("   Test 4 PASSED: Container tidak ada dilewati dengan aman!")

    browser.close()
    print("\nALL DUAL REMARKS UNIT TESTS PASSED SUCCESSFULLY!")
