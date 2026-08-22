@echo off
title Go Bo Tu Dong Khoi Dong - CheckBHYT Client
cd /d "%~dp0"

echo ====================================================================
echo    GO BO TAC VU WINDOWS TASK SCHEDULER - CHECKBHYT
echo ====================================================================
echo.

schtasks /delete /tn "CheckBHYT_Client_Runner" /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] DA GO BO TAC VU THANH CONG!
    echo [*] Client Runner se khong con tu dong chay khi khoi dong Windows.
) else (
    echo.
    echo [*] Thong bao: Tac vu chua tung duoc dang ky hoac da duoc go bo truoc do.
)

echo.
echo ====================================================================
echo.
pause
