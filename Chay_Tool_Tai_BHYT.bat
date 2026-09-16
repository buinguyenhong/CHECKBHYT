@echo off
title CheckBHYT - Cong Cu Tai Ho So BHYT Truc Tiep
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo =======================================================
echo   CHECKBHYT - CONG CU TAI & GOP DU LIEU BHYT TRUC TIEP
echo   (Khoi chay Chrome/Edge truc tiep tren may nay)
echo =======================================================
echo.

set PY_EXE=python
if exist ".venv\Scripts\python.exe" (
    set PY_EXE=.venv\Scripts\python.exe
)

cd /d "%~dp0portal_downloader"
echo [*] Dang khoi dong cong cu tai: http://localhost:8765 ...
%PY_EXE% downloader_server.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Khong the khoi chay bang .venv, dang thu voi python he thong...
    python downloader_server.py
)

pause
