import os
import sys

# ==============================================================================
# COMPATIBILITY GUARD: NumPy 2.x & openpyxl Compatibility Guard
# ==============================================================================
if getattr(sys, "frozen", False):
    for _mod in ("numpy", "scipy", "pandas", "matplotlib"):
        sys.modules[_mod] = None
else:
    try:
        import numpy as _np
        if _np is not None:
            _type_map = {
                'short': getattr(_np, 'int16', int),
                'ushort': getattr(_np, 'uint16', int),
                'intc': getattr(_np, 'int32', int),
                'uintc': getattr(_np, 'uint32', int),
                'int_': getattr(_np, 'int64', int),
                'uint': getattr(_np, 'uint64', int),
                'longlong': getattr(_np, 'int64', int),
                'ulonglong': getattr(_np, 'uint64', int),
                'half': getattr(_np, 'float16', float),
                'float16': float,
                'single': getattr(_np, 'float32', float),
                'double': getattr(_np, 'float64', float),
                'longdouble': getattr(_np, 'float64', float),
                'int8': getattr(_np, 'int8', int),
                'int16': getattr(_np, 'int16', int),
                'int32': getattr(_np, 'int32', int),
                'int64': getattr(_np, 'int64', int),
                'uint8': getattr(_np, 'uint8', int),
                'uint16': getattr(_np, 'uint16', int),
                'uint32': getattr(_np, 'uint32', int),
                'uint64': getattr(_np, 'uint64', int),
                'intp': getattr(_np, 'int64', int),
                'uintp': getattr(_np, 'uint64', int),
                'float32': float,
                'float64': float,
                'bool_': bool,
                'floating': float,
                'integer': int,
            }
            for _k, _v in _type_map.items():
                if not hasattr(_np, _k):
                    setattr(_np, _k, _v)
    except (ImportError, Exception):
        pass

from pathlib import Path

# ==============================================================================
# FASIH 3603 HELPER - GLOBAL CONFIGURATION
# ==============================================================================

APP_NAME = "FASIH 3603 Helper"
APP_VERSION = "1.8.0"
APP_SUBTITLE = "Suite Otomasi Survei & Sensus BPS Kabupaten Tangerang"
APP_AUTHOR = "BPS Kabupaten Tangerang"

# Base Directory: jika di-freeze (PyInstaller) gunakan _MEIPASS (lokasi internal bundle), fallback ke folder exe
if getattr(sys, "frozen", False):
    APP_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    EXE_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).resolve().parent
    EXE_DIR = APP_DIR

# Local AppData Directory (Data pengguna terisolasi dari folder instalasi)
USER_APPDATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "FASIH3603Helper"
CHROME_PROFILE_DIR = USER_APPDATA_DIR / "chrome_profile"
LOGS_DIR = USER_APPDATA_DIR / "logs"
AUDIT_DIR = USER_APPDATA_DIR / "audit_trail"
BACKUP_DIR = USER_APPDATA_DIR / "backups"

# Assets Directory
ASSETS_DIR = APP_DIR / "assets"
if not ASSETS_DIR.exists() and (EXE_DIR / "assets").exists():
    ASSETS_DIR = EXE_DIR / "assets"

APP_ICON_ICO = ASSETS_DIR / "app_icon.ico"
APP_LOGO_PNG = ASSETS_DIR / "app_logo.png"
APP_LOGO_36 = ASSETS_DIR / "logo_36.png"
APP_LOGO_64 = ASSETS_DIR / "logo_64.png"

# Browser Profile & Settings Directories
BROWSER_CHROME = "chrome"
BROWSER_EDGE = "edge"
DEFAULT_BROWSER = BROWSER_CHROME

# Feature Flags
ENABLE_INCOGNITO_MODE = False  # Dinonaktifkan sementara sesuai kebutuhan pengguna

EDGE_PROFILE_DIR = USER_APPDATA_DIR / "edge_profile"
SETTINGS_FILE = USER_APPDATA_DIR / "settings.json"

# Pastikan folder data pengguna dibuat
for d in [USER_APPDATA_DIR, CHROME_PROFILE_DIR, EDGE_PROFILE_DIR, LOGS_DIR, AUDIT_DIR, BACKUP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Port & URL Remote Debugging CDP
DEFAULT_CDP_HOST = "127.0.0.1"
CHROME_CDP_PORT = 9222
EDGE_CDP_PORT = 9223
DEFAULT_CDP_PORT = CHROME_CDP_PORT
CDP_URL = f"http://{DEFAULT_CDP_HOST}:{DEFAULT_CDP_PORT}"

# Browser Launcher Paths
CHROME_PATHS = [
    Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google\\Chrome\\Application\\chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google\\Chrome\\Application\\chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google\\Chrome\\Application\\chrome.exe",
]

EDGE_PATHS = [
    Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Microsoft\\Edge\\Application\\msedge.exe",
    Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Microsoft\\Edge\\Application\\msedge.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft\\Edge\\Application\\msedge.exe",
]

# Backward compatibility alias
CHROME_CANDIDATE_PATHS = CHROME_PATHS + EDGE_PATHS

# Common Anti-Detection & Anti-Throttling Flags
BASE_BROWSER_FLAGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    # Anti-throttling saat browser di-minimize / background
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-background-timer-throttling",
    "--no-first-run",
    "--no-default-browser-check",
]

CHROME_FLAGS = [
    f"--remote-debugging-port={DEFAULT_CDP_PORT}",
    f"--user-data-dir={str(CHROME_PROFILE_DIR)}",
] + BASE_BROWSER_FLAGS
