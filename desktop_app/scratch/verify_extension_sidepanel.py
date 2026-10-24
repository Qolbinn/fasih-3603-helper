import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ext_path = Path(r"d:\3603 BPS Kab Tangerang\2026\Sensus Ekonomi\Anomali\Fasih 3603 Helper\browser_extension").resolve()
print(f"Testing extension at: {ext_path}")

test_user_data = ext_path.parent / "scratch" / "test_user_data"
test_user_data.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        str(test_user_data),
        channel="chrome",
        headless=False,
        args=[
            f"--disable-extensions-except={ext_path}",
            f"--load-extension={ext_path}",
        ]
    )
    
    # Tunggu service worker terdaftar
    page = browser.new_page()
    page.wait_for_timeout(2000)
    
    # Buka management API atau internal page
    page.goto("https://fasih-sm.bps.go.id/app")
    page.wait_for_timeout(1000)
    
    ext_id = None
    if browser.service_workers:
        for sw in browser.service_workers:
            if "chrome-extension://" in sw.url:
                ext_id = sw.url.split("/")[2]
                break

    if not ext_id:
        page.goto("chrome://extensions")
        page.wait_for_timeout(1000)
        ext_id = page.evaluate("""() => {
            const manager = document.querySelector('extensions-manager');
            if (manager && manager.shadowRoot) {
                const itemList = manager.shadowRoot.querySelector('extensions-item-list');
                if (itemList && itemList.shadowRoot) {
                    const item = itemList.shadowRoot.querySelector('extensions-item');
                    if (item) return item.id;
                }
            }
            return null;
        }""")
                
    print(f"Extension ID: {ext_id}")
    
    if ext_id:
        sidepanel_url = f"chrome-extension://{ext_id}/sidepanel/sidepanel.html"
        print(f"Navigating to sidepanel: {sidepanel_url}")
        
        js_errors = []
        page.on("pageerror", lambda err: js_errors.append(str(err)))
        page.on("console", lambda msg: print(f"[Browser Console {msg.type}] {msg.text}"))
        
        page.goto(sidepanel_url)
        page.wait_for_timeout(1500)
        
        # Evaluasi DOM dan namespace
        eval_result = page.evaluate("""() => {
            return {
                title: document.title,
                hasXLSX: typeof XLSX !== 'undefined',
                hasModulesConfig: typeof MODULES_CONFIG !== 'undefined',
                modulesCount: typeof MODULES_CONFIG !== 'undefined' ? Object.keys(MODULES_CONFIG).length : 0,
                hasExcelIO: typeof ExcelIO !== 'undefined',
                hasOrchestrator: typeof Orchestrator !== 'undefined',
                selectOptions: Array.from(document.querySelectorAll('#module-select option')).map(o => o.value)
            };
        }""")
        
        print("\n--- Evaluation Result ---")
        for k, v in eval_result.items():
            print(f"{k}: {v}")
            
        if js_errors:
            print(f"\n❌ JavaScript Errors detected ({len(js_errors)}):")
            for e in js_errors:
                print(f"  - {e}")
            sys.exit(1)
        else:
            print("\n✅ Sidepanel loaded cleanly with 0 JavaScript errors!")
            
    browser.close()
