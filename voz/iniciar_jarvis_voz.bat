@echo off
cd /d "%~dp0"
set "PATH=%PATH%;%USERPROFILE%\.local\bin"
python jarvis_voz.py
pause
