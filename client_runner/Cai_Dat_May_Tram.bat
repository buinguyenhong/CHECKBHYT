@echo off
chcp 65001 >nul
title Cai Dat CheckBHYT Client RPA Runner
echo ====================================================================
echo    CAI DAT BO CONG CU RPA CHO MAY TRAM (CLIENT PC) - CHECKBHYT     
echo ====================================================================
echo.
echo [*] BƯỚC 1/2: Đang cài đặt thư viện Python (requests, pandas, openpyxl, playwright)...
python -m pip install --upgrade pip
python -m pip install requests pandas openpyxl playwright
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] LOI: Khong the cai dat thu vien Python. Vui long kiem tra lai ket noi mang.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [*] BƯỚC 2/2: Đang tải và cài đặt trình duyệt Chromium Playwright...
python -m playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] LOI: Khong the cai dat trinh duyet Chromium.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ====================================================================
echo    CÀI ĐẶT THÀNH CÔNG 100%!
echo    BÂY GIỜ BẠN CÓ THỂ CHẠY FILE:
echo    "Chay_RPA_May_Tram.bat" ĐỂ KẾT NỐI TỰ ĐỘNG VỚI WEB APP.
echo ====================================================================
echo.
pause
