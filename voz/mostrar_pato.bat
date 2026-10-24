@echo off
rem Vuelve a mostrar a Pato (o lo lanza si no esta abierto)
cd /d "%~dp0"
echo mostrar> mascota_cmd.txt
powershell -NoProfile -Command "if (-not (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like *mascota_pato.py* })) { Start-Process -WindowStyle Hidden -FilePath %LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe -ArgumentList mascota_pato.py -WorkingDirectory %~dp0 }"
