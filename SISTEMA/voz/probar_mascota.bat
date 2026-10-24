@echo off
cd /d "%~dp0"
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*mascota_pato*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
"%PY%" mascota_pato.py --demo > mascota_demo.log 2>&1
