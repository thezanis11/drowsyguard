@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Lancez Installer.bat d'abord.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m drowsyguard run %*
if errorlevel 1 pause

