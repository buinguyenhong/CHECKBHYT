@echo off
chcp 65001 >nul
title CheckBHYT Client RPA Runner - Local Web Bridge (Port 8765)
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"

echo ====================================================================
echo    CHECKBHYT - CLIENT RPA RUNNER (LOCAL WEB BRIDGE)
echo ====================================================================
echo.
echo [*] Đang khởi động tiến trình cầu nối Local Bridge tại cổng 8765...
echo [*] Vui lòng KHÔNG đóng cửa sổ này trong khi sử dụng Web App.
echo.

python "%~dp0client_agent.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ====================================================================
    echo [!] PHÁT HIỆN LỖI KHỞI ĐỘNG: Mã lỗi %ERRORLEVEL%
    echo [*] Gợi ý: Nếu chưa cài đặt thư viện, hãy chạy file "Cai_Dat_May_Tram.bat" trước!
    echo ====================================================================
    pause
)
