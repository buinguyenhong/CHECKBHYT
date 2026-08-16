@echo off
chcp 65001 >nul
title CheckBHYT Client RPA Runner
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
start pythonw "%~dp0client_agent.py"
if %ERRORLEVEL% NEQ 0 (
    python "%~dp0client_agent.py"
)
exit
