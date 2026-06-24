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
powershell -NoProfile -Command "Write-Host '[INFO] Build/update offline wheelhouse in 10 seconds. Press any key to skip.' -ForegroundColor Cyan"
timeout /t 10 >nul
if errorlevel 1 goto skip_wheelhouse
set JPL_CAD_SKIP_PAUSE=1
call build_wheelhouse_windows.bat /auto
if errorlevel 1 (
  powershell -NoProfile -Command "Write-Host '[WARN] Wheelhouse build failed or was incomplete. The app can still start; see install logs above.' -ForegroundColor DarkYellow"
)
:skip_wheelhouse
powershell -NoProfile -Command "Write-Host '[OK] Starting app in 10 seconds. Press Ctrl+C to cancel.' -ForegroundColor Green"
timeout /t 10
call run_windows.bat
