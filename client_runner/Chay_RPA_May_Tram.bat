@echo off
title CheckBHYT Client RPA Runner - Local Web Bridge (Port 8765)
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ====================================================================
echo    CHECKBHYT - CLIENT RPA RUNNER (LOCAL WEB BRIDGE)
echo ====================================================================
echo.
echo [*] Dang khoi dong tien trinh cau noi Local Bridge tai cong 8765...
echo [*] Vui long KHONG dong cua so nay trong khi su dung Web App.
echo.

python "%~dp0client_agent.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ====================================================================
    echo [!] PHAT HIEN LOI KHOI DONG: Ma loi %ERRORLEVEL%
    echo [*] Goi y: Neu chua cai dat thu vien, hay chay file "Cai_Dat_May_Tram.bat" truoc!
    echo ====================================================================
    pause
)
