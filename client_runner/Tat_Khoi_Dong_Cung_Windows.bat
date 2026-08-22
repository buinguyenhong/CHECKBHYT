@echo off
title Tat Tu Dong Khoi Dong Cung Windows
cd /d "%~dp0"

echo ====================================================================
echo    TAT TU DONG KHOI DONG CUNG WINDOWS - CHECKBHYT CLIENT
echo ====================================================================
echo.

set "VBS_FILE=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\CheckBHYT_Client_Runner.vbs"

if exist "%VBS_FILE%" (
    del /f /q "%VBS_FILE%"
    echo [OK] DA GO BO THANH CONG!
    echo [*] CheckBHYT Client Runner se khong con tu dong chay khi bat may nua.
) else (
    echo [*] Thong bao: Chua cai dat tu dong khoi dong truoc do.
)

echo.
echo ====================================================================
echo.
pause
