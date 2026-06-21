@echo off
setlocal EnableExtensions
chcp 65001 >nul
powershell -NoProfile -Command "Write-Host '========================================================================' -ForegroundColor Cyan; Write-Host '  JPL CAD Ollama Explorer - offline install from wheelhouse' -ForegroundColor Cyan; Write-Host '========================================================================' -ForegroundColor Cyan"
set PYLAUNCH=py -3.11
%PYLAUNCH% --version >nul 2>nul
if errorlevel 1 set PYLAUNCH=py -3.10
%PYLAUNCH% --version >nul 2>nul
if errorlevel 1 set PYLAUNCH=python
%PYLAUNCH% scripts\setup_env.py offline
if errorlevel 1 (
  powershell -NoProfile -Command "Write-Host '[ERROR] Offline setup failed. Build/copy wheelhouse first.' -ForegroundColor Red"
  pause
  exit /b 1
)
call run_windows.bat
