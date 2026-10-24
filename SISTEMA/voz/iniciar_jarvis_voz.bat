@echo off
cd /d "%~dp0"
set "PATH=%PATH%;%APPDATA%\npm"
python jarvis_voz.py
pause
