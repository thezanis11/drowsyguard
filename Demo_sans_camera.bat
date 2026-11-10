@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m drowsyguard demo %*
if errorlevel 1 pause

