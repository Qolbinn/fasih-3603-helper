# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:/2026/Sensus Ekonomi/fasih-3603-helper/desktop_app/main.py'],
    pathex=['C:/Users/arzud/anaconda3/envs/automation/Library/bin'],
    binaries=[],
    datas=[('C:/Users/arzud/anaconda3/envs/automation/Lib/site-packages/customtkinter', 'customtkinter'), ('D:/2026/Sensus Ekonomi/fasih-3603-helper/desktop_app/assets', 'assets')],
    hiddenimports=['customtkinter', 'playwright', 'openpyxl', 'win32gui', 'win32con', 'win32process', 'psutil', 'modules.cleaning_usaha', 'modules.dc_usaha_#3603', 'modules.approve_se2026', 'modules.remark_kbli', 'modules.kbli_sembako', 'modules.cleaning_nik_r30', 'modules.cleaning_nik_r29', 'modules.cleaning_nik_r27', 'modules.kbli_pmm', 'modules.kbli_kategori_A', 'modules.kbli_air_11502'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'scipy', 'pandas', 'matplotlib'],
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
    icon=['D:/2026/Sensus Ekonomi/fasih-3603-helper/desktop_app/assets/app_icon.ico'],
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
