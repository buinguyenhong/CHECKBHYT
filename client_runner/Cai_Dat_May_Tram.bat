@echo off
title Cai Dat CheckBHYT Client RPA Runner
cd /d "%~dp0"

echo ====================================================================
echo    CAI DAT BO CONG CU RPA CHO MAY TRAM (CLIENT PC) - CHECKBHYT     
echo ====================================================================
echo.
echo [*] BUOC 1/2: Dang cai dat thu vien Python (requests, pandas, openpyxl, playwright)...
python -m pip install --upgrade pip
python -m pip install requests pandas openpyxl playwright
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] LOI: Khong the cai dat thu vien Python. Vui long kiem tra lai ket noi mang hoac quyen Administrator.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [*] BUOC 2/2: Dang tai va cai dat trinh duyet Chromium Playwright...
python -m playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] LOI: Khong the cai dat trinh duyet Chromium.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ====================================================================
echo    CAI DAT THANH CONG 100%!
echo    BAY GIO BAN CO THE CHAY FILE:
echo    "Chay_RPA_May_Tram.bat" DE KET NOI TU DONG VOI WEB APP.
echo ====================================================================
echo.
pause
