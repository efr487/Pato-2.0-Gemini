@echo off
setlocal
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if not exist "%PY%" set "PY=pythonw"
set "PID="
if exist jarvis.pid set /p PID=<jarvis.pid
if "%PID%"=="" goto iniciar
tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul
if errorlevel 1 goto iniciar
rem --- Estaba en marcha: lo desactiva ---
taskkill /PID %PID% /F >nul 2>&1
del jarvis.pid >nul 2>&1
powershell -NoProfile -Command "[console]::beep(500,200); [console]::beep(350,300)"
exit /b
:iniciar
rem --- No estaba en marcha: lo activa (sin ventana de consola) ---
del jarvis.pid >nul 2>&1
start "" "%PY%" jarvis_voz.py
exit /b
