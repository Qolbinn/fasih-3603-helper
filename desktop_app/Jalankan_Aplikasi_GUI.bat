@echo off
title FASIH 3603 Helper Launcher
cd /d "%~dp0"
echo ========================================================
echo       Meluncurkan FASIH 3603 Helper Desktop...
echo ========================================================

set "PYTHON_EXE="

if exist "%USERPROFILE%\anaconda3\envs\automation\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\anaconda3\envs\automation\python.exe"
) else if exist "C:\Users\Qolbin\anaconda3\envs\automation\python.exe" (
    set "PYTHON_EXE=C:\Users\Qolbin\anaconda3\envs\automation\python.exe"
) else if exist "%USERPROFILE%\anaconda3\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\anaconda3\python.exe"
) else if exist "%USERPROFILE%\miniconda3\envs\automation\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\miniconda3\envs\automation\python.exe"
) else if exist "%USERPROFILE%\miniconda3\python.exe" (
    set "PYTHON_EXE=%USERPROFILE%\miniconda3\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo Menggunakan Python: %PYTHON_EXE%
echo.

"%PYTHON_EXE%" "main.py"
if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo Terjadi kendala saat menjalankan aplikasi.
    echo Pastikan environment Python/Conda Anda telah terpasang
    echo dan pustaka (customtkinter, playwright, dll) sudah diinstall.
    echo ========================================================
    pause
)
