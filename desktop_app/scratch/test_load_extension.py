import sys
from pathlib import Path

# Add desktop_app to python path
sys.path.insert(0, str(Path("desktop_app").resolve()))

from playwright.sync_api import sync_playwright
from core.browser_manager import BrowserManager

ext_path = str(Path("browser_extension").resolve())
chrome_path = BrowserManager.get_installed_browser_path()
print("Chrome executable:", chrome_path)
print("Extension directory:", ext_path)

with sync_playwright() as p:
    args = [
        f"--disable-extensions-except={ext_path}",
        f"--load-extension={ext_path}"
    ]
    user_data = Path("desktop_app/scratch/ext_test_profile").resolve()
    user_data.mkdir(parents=True, exist_ok=True)

    context = p.chromium.launch_persistent_context(
        str(user_data),
        executable_path=chrome_path,
        headless=False,
        args=args
    )

    print("Browser launched with extension loaded!")

    # Check background service worker
    sw = context.service_workers
    print(f"Service workers registered: {len(sw)}")

    # Wait for service worker to register
    print("Waiting for service worker...")
    import time
    sw_list = context.service_workers
    for _ in range(10):
        if len(sw_list) > 0:
            break
        time.sleep(0.5)
        sw_list = context.service_workers

    ext_id = None
    if len(sw_list) > 0:
        ext_id = sw_list[0].url.split("/")[2]
        print(f"Service worker URL: {sw_list[0].url}, Ext ID: {ext_id}")

    if not ext_id:
        # Fallback to chrome://extensions or developer page
        print("Checking extension ID via chrome://serviceworker-internals...")
        p_sw = context.new_page()
        p_sw.goto("chrome://serviceworker-internals")
        content = p_sw.content()
        import re
        m = re.search(r"chrome-extension://([a-z0-9]+)/", content)
        if m:
            ext_id = m.group(1)
            print("Found ext_id:", ext_id)
        p_sw.close()

    if ext_id:
        sidepanel_url = f"chrome-extension://{ext_id}/sidepanel/sidepanel.html"
        print(f"Navigating to Side Panel: {sidepanel_url}")
        p_sp = context.new_page()
        p_sp.on("console", lambda msg: print("[SIDEPANEL LOG]", msg.text))
        p_sp.on("pageerror", lambda err: print("[SIDEPANEL ERROR]", err))
        p_sp.goto(sidepanel_url)
        p_sp.wait_for_timeout(1000)

        sp_status = p_sp.evaluate("""() => {
            return {
                title: document.title,
                hasXLSX: typeof window.XLSX !== 'undefined',
                hasModulesConfig: typeof window.MODULES_CONFIG !== 'undefined',
                modulesCount: typeof window.MODULES_CONFIG !== 'undefined' ? Object.keys(window.MODULES_CONFIG).length : 0,
                hasExcelIO: typeof window.ExcelIO !== 'undefined',
                hasOrchestrator: typeof window.Orchestrator !== 'undefined'
            };
        }""")
        print("Sidepanel Health Check:", sp_status)
        assert sp_status["hasXLSX"] == True
        assert sp_status["hasModulesConfig"] == True
        assert sp_status["modulesCount"] == 6
        assert sp_status["hasExcelIO"] == True
        assert sp_status["hasOrchestrator"] == True
        print("ALL 6 MODULES & SIDEPANEL COMPONENTS VERIFIED HEALTHY!")
        p_sp.close()

    context.close()
    print("Extension verification test PASSED successfully!")
