@echo off
rem Run without console window. Use run_debug.bat to see logs.
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Run setup\install.ps1 first
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m app
