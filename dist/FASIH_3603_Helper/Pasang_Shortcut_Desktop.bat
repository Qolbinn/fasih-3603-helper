@echo off
chcp 65001 >nul
title Memasang Shortcut FASIH 3603 Helper
echo ======================================================================
echo           MEMASANG SHORTCUT DESKTOP - FASIH 3603 HELPER
echo ======================================================================
echo.

set "APP_DIR=%~dp0"
set "TARGET_EXE=%APP_DIR%FASIH_3603_Helper.exe"
set "ICON_FILE=%APP_DIR%assets\app_icon.ico"

if not exist "%TARGET_EXE%" (
    echo [ERROR] File FASIH_3603_Helper.exe tidak ditemukan di folder ini!
    echo Pastikan file batch ini berada di dalam folder yang sama dengan FASIH_3603_Helper.exe.
    echo.
    pause
    exit /b 1
)

echo Membuat shortcut di Desktop Anda...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $desktopPath = [System.Environment]::GetFolderPath('Desktop'); ^
     $shortcutPath = Join-Path -Path $desktopPath -ChildPath 'FASIH 3603 Helper.lnk'; ^
     $shortcut = $ws.CreateShortcut($shortcutPath); ^
     $shortcut.TargetPath = '%TARGET_EXE%'; ^
     $shortcut.WorkingDirectory = '%APP_DIR%'; ^
     $shortcut.IconLocation = '%ICON_FILE%'; ^
     $shortcut.Description = 'Aplikasi Otomasi Fasih 3603 BPS Kabupaten Tangerang'; ^
     $shortcut.Save();"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================================================
    echo [SUKSES] Shortcut 'FASIH 3603 Helper' berhasil dipasang di Desktop!
    echo Ikon aplikasi sudah otomatis terpasang.
    echo Anda kini dapat langsung membuka aplikasi dari Desktop.
    echo ======================================================================
) else (
    echo.
    echo [GAGAL] Terjadi kesalahan saat membuat shortcut.
)

echo.
pause
