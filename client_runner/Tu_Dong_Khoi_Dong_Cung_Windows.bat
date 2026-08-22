@echo off
title Cai Dat Tu Dong Khoi Dong Cung Windows
cd /d "%~dp0"

echo ====================================================================
echo    CAI DAT TU DONG KHOI DONG CUNG WINDOWS - CHECKBHYT CLIENT
echo ====================================================================
echo.

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS_FILE=%STARTUP_FOLDER%\CheckBHYT_Client_Runner.vbs"
set "AGENT_SCRIPT=%~dp0client_agent.py"

echo [*] Dang tao tap tin khoi dong ngam tai:
echo     "%VBS_FILE%"
echo.

(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run "pythonw """ ^& "%AGENT_SCRIPT%" ^& """", 0, False
) > "%VBS_FILE%"

if %ERRORLEVEL% EQU 0 (
    echo [OK] DA CAI DAT THANH CONG!
    echo.
    echo [*] Tu nay ve sau, moi khi ban bat may tinh, CheckBHYT Client Runner
    echo     se tu dong chay ngam san sang ket noi voi Web App.
) else (
    echo [!] LOI: Khong the tao file khoi dong trong thu muc Startup.
)

echo.
echo ====================================================================
echo.
pause
