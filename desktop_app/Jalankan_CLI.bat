@echo off
title FASIH 3603 Helper - CLI Runner
cd /d "%~dp0"
echo ========================================================
echo       Meluncurkan FASIH 3603 Helper (CLI Runner)...
echo ========================================================
"C:\Users\Qolbin\anaconda3\envs\automation\python.exe" "cli_runner.py" %*
pause
