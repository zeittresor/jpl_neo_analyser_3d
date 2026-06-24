@echo off
setlocal EnableExtensions
chcp 65001 >nul
if /i "%~1"=="/auto" set JPL_CAD_SKIP_PAUSE=1
powershell -NoProfile -Command "Write-Host '========================================================================' -ForegroundColor Cyan; Write-Host '  JPL CAD Ollama Explorer - build wheelhouse' -ForegroundColor Cyan; Write-Host '========================================================================' -ForegroundColor Cyan"
set PYLAUNCH=py -3.11
%PYLAUNCH% --version >nul 2>nul
if errorlevel 1 set PYLAUNCH=py -3.10
%PYLAUNCH% --version >nul 2>nul
if errorlevel 1 set PYLAUNCH=python
%PYLAUNCH% scripts\setup_env.py wheelhouse
set BUILD_EXIT=%ERRORLEVEL%
if not "%JPL_CAD_SKIP_PAUSE%"=="1" pause
exit /b %BUILD_EXIT%
