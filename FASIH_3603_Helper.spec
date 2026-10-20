# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/3603 BPS Kab Tangerang/2026/Sensus Ekonomi/Anomali/Fasih 3603 Helper/main.py'],
    pathex=['C:/Users/Qolbin/anaconda3/envs/automation/Library/bin'],
    binaries=[],
    datas=[('C:/Users/Qolbin/anaconda3/envs/automation/Lib/site-packages/customtkinter', 'customtkinter'), ('D:/3603 BPS Kab Tangerang/2026/Sensus Ekonomi/Anomali/Fasih 3603 Helper/assets', 'assets')],
    hiddenimports=['customtkinter', 'playwright', 'openpyxl', 'win32gui', 'win32con', 'win32process', 'psutil', 'modules.data_cleaning', 'modules.approve_se2026'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FASIH_3603_Helper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/3603 BPS Kab Tangerang/2026/Sensus Ekonomi/Anomali/Fasih 3603 Helper/assets/app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FASIH_3603_Helper',
)
