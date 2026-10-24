import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright
from modules.kbli_pmm.engine import _process_pmm_characteristics

HTML_WITH_WARNING = """
<!DOCTYPE html>
<html>
<head><title>Test PMM Warning</title></head>
<body>
  <!-- 13. b1: produk_sendiri -->
  <div id="produk_sendiri#1001">
    <div role="radiogroup">
      <div role="group">
        <input type="radio" name="rg1" value="1" id="rg1-1"><label for="rg1-1">1. Ya</label>
      </div>
      <div role="group">
        <input type="radio" name="rg1" value="2" id="rg1-2"><label for="rg1-2">2. Tidak</label>
      </div>
    </div>
  </div>

  <!-- 13. b2: layanan_mamin -->
  <div id="layanan_mamin#1001">
    <div role="radiogroup">
      <div role="group">
        <input type="radio" name="rg2" value="1" id="rg2-1"><label for="rg2-1">1. Ya</label>
      </div>
      <div role="group">
        <input type="radio" name="rg2" value="2" id="rg2-2"><label for="rg2-2">2. Tidak</label>
      </div>
    </div>
  </div>

  <!-- 13. c: lokasi_usaha WITH WARNING KELILING -->
  <div id="lokasi_usaha#1001">
    <div role="radiogroup">
      <div role="group">
        <input type="radio" name="rg3" value="05" id="rg3-5"><label for="rg3-5">5.  Kedai, stan, tenda</label>
      </div>
      <div role="group">
        <input type="radio" name="rg3" value="09" id="rg3-9"><label for="rg3-9">9. Restoran, warung makan, dan sejenisnya</label>
      </div>
      <div role="group">
        <input type="radio" name="rg3" value="10" id="rg3-10"><label for="rg3-10">10. Keliling</label>
      </div>
    </div>
    <div class="tw:space-y-2 tw:font-bold tw:text-xs tw:text-destructive">
      <div class="tw:flex tw:flex-row tw:items-start tw:space-x-2">
        <span>Jika R.9a diisi kode 2 (Usaha Keliling), maka R.13c diisi kode 10 (Usaha Keliling)</span>
      </div>
    </div>
  </div>
</body>
</html>
"""

HTML_WITHOUT_WARNING = """
<!DOCTYPE html>
<html>
<head><title>Test PMM Normal</title></head>
<body>
  <div id="produk_sendiri#2001">
    <div role="radiogroup">
      <div role="group">
        <input type="radio" name="rg1" value="1" id="rg1-1"><label for="rg1-1">1. Ya</label>
      </div>
      <div role="group">
        <input type="radio" name="rg1" value="2" id="rg1-2"><label for="rg1-2">2. Tidak</label>
      </div>
    </div>
  </div>

  <div id="layanan_mamin#2001">
    <div role="radiogroup">
      <div role="group">
        <input type="radio" name="rg2" value="1" id="rg2-1"><label for="rg2-1">1. Ya</label>
      </div>
      <div role="group">
        <input type="radio" name="rg2" value="2" id="rg2-2"><label for="rg2-2">2. Tidak</label>
      </div>
    </div>
  </div>

  <div id="lokasi_usaha#2001">
    <div role="radiogroup">
      <div role="group">
        <input type="radio" name="rg3" value="05" id="rg3-5"><label for="rg3-5">5.  Kedai, stan, tenda</label>
      </div>
      <div role="group">
        <input type="radio" name="rg3" value="09" id="rg3-9"><label for="rg3-9">9. Restoran, warung makan, dan sejenisnya</label>
      </div>
      <div role="group">
        <input type="radio" name="rg3" value="10" id="rg3-10"><label for="rg3-10">10. Keliling</label>
      </div>
    </div>
  </div>
</body>
</html>
"""

from core.browser_manager import BrowserManager

with sync_playwright() as p:
    chrome_path = BrowserManager.get_installed_browser_path()
    browser = p.chromium.launch(executable_path=chrome_path, headless=True)
    page = browser.new_page()

    # TEST 1: KBLI 56102 dengan Warning Usaha Keliling
    print("Testing 1: KBLI 56102 dengan Warning Usaha Keliling...")
    page.set_content(HTML_WITH_WARNING)
    ok, st, ket = _process_pmm_characteristics(page, kbli_akhir="56102", worker_prefix="[TEST] ")
    print(f"Result 1: ok={ok}, st={st}, ket={ket}")
    assert ok is True
    assert "10. Keliling" in ket
    # Verifikasi input value 10 tercentang di DOM
    inp_10 = page.locator("input[value='10']").first
    assert inp_10.is_checked()
    print("   Test 1 PASSED: Terpilih '10. Keliling'!")

    # TEST 2: KBLI 56102 TANPA Warning Usaha Keliling
    print("Testing 2: KBLI 56102 TANPA Warning Usaha Keliling...")
    page.set_content(HTML_WITHOUT_WARNING)
    ok, st, ket = _process_pmm_characteristics(page, kbli_akhir="56102", worker_prefix="[TEST] ")
    print(f"Result 2: ok={ok}, st={st}, ket={ket}")
    assert ok is True
    assert "5. Kedai, stan, tenda" in ket
    inp_05 = page.locator("input[value='05']").first
    assert inp_05.is_checked()
    print("   Test 2 PASSED: Terpilih '5. Kedai, stan, tenda'!")

    # TEST 3: KBLI 56101 (Restoran)
    print("Testing 3: KBLI 56101 (Restoran)...")
    page.set_content(HTML_WITHOUT_WARNING)
    ok, st, ket = _process_pmm_characteristics(page, kbli_akhir="56101", worker_prefix="[TEST] ")
    print(f"Result 3: ok={ok}, st={st}, ket={ket}")
    assert ok is True
    assert "9. Restoran, warung makan, dan sejenisnya" in ket
    inp_09 = page.locator("input[value='09']").first
    assert inp_09.is_checked()
    print("   Test 3 PASSED: Terpilih '9. Restoran, warung makan, dan sejenisnya'!")

    browser.close()
    print("\nALL PMM CHARACTERISTICS TESTS WITH USABILITY VERIFICATION PASSED!")
