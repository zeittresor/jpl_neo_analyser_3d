@echo off
setlocal EnableExtensions
chcp 65001 >nul
cls
powershell -NoProfile -Command "Write-Host '========================================================================' -ForegroundColor Cyan; Write-Host '  JPL CAD Ollama Explorer - install / repair' -ForegroundColor Cyan; Write-Host '========================================================================' -ForegroundColor Cyan"
set PYLAUNCH=py -3.11
%PYLAUNCH% --version >nul 2>nul
if errorlevel 1 set PYLAUNCH=py -3.10
%PYLAUNCH% --version >nul 2>nul
if errorlevel 1 set PYLAUNCH=python
%PYLAUNCH% --version
%PYLAUNCH% scripts\setup_env.py install
if errorlevel 1 (
  powershell -NoProfile -Command "Write-Host '[ERROR] Setup failed.' -ForegroundColor Red"
  pause
  exit /b 1
)
powershell -NoProfile -Command "Write-Host '[OK] Starting app in 10 seconds. Press Ctrl+C to cancel.' -ForegroundColor Green"
timeout /t 10
call run_windows.bat
