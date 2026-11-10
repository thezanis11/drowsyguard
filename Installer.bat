@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if errorlevel 1 goto error
if exist requirements-lock.txt (set "DROWSY_REQUIREMENTS=requirements-lock.txt") else (set "DROWSY_REQUIREMENTS=requirements.txt")
".venv\Scripts\python.exe" -m pip install --no-cache-dir --only-binary=:all: -r "%DROWSY_REQUIREMENTS%"
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m drowsyguard download
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m drowsyguard doctor
if errorlevel 1 goto error
echo Installation terminee. Lancez Demarrer.bat pour utiliser la webcam.
pause
exit /b 0
:error
echo Installation interrompue. Verifiez Python 3.12, Internet et l'espace disque.
pause
exit /b 1

