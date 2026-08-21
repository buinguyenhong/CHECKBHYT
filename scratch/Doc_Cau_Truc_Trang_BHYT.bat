@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
title DOC CAU TRUC DOM CONG BHYT
cls
echo ======================================================================
echo DANG KHOI CHAY TRINH DUYET CHROMIUM DE DOC DOM CONG BHYT...
echo ======================================================================
echo.
python inspect_bhyt_live.py
echo.
echo ======================================================================
echo Nhan phim bat ky de dong cua so...
pause >nul
