@echo off
setlocal EnableExtensions
chcp 65001 >nul
if not exist .venv\Scripts\python.exe (
  echo [ERROR] .venv not found. Run install_windows.bat first.
  pause
  exit /b 1
)
set PYTHONPATH=%CD%\src
.venv\Scripts\python.exe app.py
if errorlevel 1 pause
