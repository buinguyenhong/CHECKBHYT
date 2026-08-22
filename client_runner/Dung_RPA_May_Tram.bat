@echo off
title Dung CheckBHYT Client RPA Runner
cd /d "%~dp0"

echo ====================================================================
echo    DUNG CHECKBHYT CLIENT RPA RUNNER (TAT TIEN TRINH NGAM)
echo ====================================================================
echo.

echo [*] Dang tim va dung tien trinh client_agent.py...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*client_agent.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

echo.
echo [OK] DA DUNG THANH CONG TIEN TRINH CLIENT RUNNER!
echo.
pause
