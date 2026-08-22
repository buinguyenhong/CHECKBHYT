@echo off
title Cai Dat Tu Dong Khoi Dong - CheckBHYT Client
cd /d "%~dp0"

echo ====================================================================
echo    DANG KY TAC VU HE THONG WINDOWS TASK SCHEDULER - CHECKBHYT
echo ====================================================================
echo.

:: Xoa tac vu cu neu da ton tai
schtasks /delete /tn "CheckBHYT_Client_Runner" /f >nul 2>&1

:: Dang ky tac vu moi chay khi dang nhap Windows
schtasks /create /tn "CheckBHYT_Client_Runner" /tr "pythonw.exe \"%~dp0client_agent.py\"" /sc onlogon /rl limited /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] DA DANG KY TAC VU WINDOWS TASK SCHEDULER THANH CONG!
    echo [*] CheckBHYT Client Runner se tu dong khoi chay ngam moi khi ban dang nhap.
    echo [*] Day la co che tieu chuan Microsoft, an toan 100%% va khong bi Antivirus chan.
) else (
    echo.
    echo [!] LOI: Khong the tao tac vu. Hay thu Chay voi quyen Administrator (Run as Administrator).
)

echo.
echo ====================================================================
echo.
pause
