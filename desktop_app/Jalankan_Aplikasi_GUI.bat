@echo off
title FASIH 3603 Helper Launcher
cd /d "%~dp0"
echo ========================================================
echo       Meluncurkan FASIH 3603 Helper Desktop...
echo ========================================================
"C:\Users\Qolbin\anaconda3\envs\automation\python.exe" "main.py"
if %errorlevel% neq 0 (
    echo.
    echo Terjadi kendala saat menjalankan aplikasi.
    pause
)
