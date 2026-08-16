@echo off
chcp 65001 >nul
title Cai Dat CheckBHYT Client RPA Runner
echo ====================================================================
echo    CÀI ĐẶT BỘ CÔNG CỤ RPA CHO MÁY TRẠM (CLIENT PC) - CHECKBHYT     
echo ====================================================================
echo.
echo [*] BƯỚC 1/2: Đang cài đặt thư viện Python (requests, pandas, playwright)...
python -m pip install --upgrade pip
python -m pip install -r "%~dp0requirements_client.txt"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] LỖI: Không thể cài đặt thư viện Python. Vui lòng kiểm tra lại kết nối mạng.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [*] BƯỚC 2/2: Đang tải và cài đặt trình duyệt Chromium Playwright...
python -m playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] LỖI: Không thể cài đặt trình duyệt Chromium.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ====================================================================
echo    CÀI ĐẶT THÀNH CÔNG 100%! BÂY GIỜ BẠN CÓ THỂ CHẠY FILE:
echo    "Chay_RPA_May_Tram.bat" ĐỂ MỞ CÔNG CỤ TỰ ĐỘNG HÓA.
echo ====================================================================
echo.
pause
