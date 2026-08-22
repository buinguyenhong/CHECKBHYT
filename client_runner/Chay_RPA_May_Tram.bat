@echo off
title Khoi Dong CheckBHYT Client RPA Runner
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo [*] Dang khoi dong CheckBHYT Client RPA Runner chay ngam...
start "" pythonw "%~dp0client_agent.py"
if %ERRORLEVEL% NEQ 0 (
    start "" python "%~dp0client_agent.py"
)

echo [OK] Tien trinh da duoc khoi dong chay ngam tai cong 8765.
echo [*] Cua so nay se tu dong dong sau 2 giay...
timeout /t 2 /nobreak >nul
exit
