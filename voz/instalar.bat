@echo off
cd /d "%~dp0"
echo Instalando dependencias de Jarvis por voz...
python -m pip install --upgrade pip
python -m pip install vosk sounddevice numpy keyboard edge-tts faster-whisper piper-tts
echo.
echo Listo. Ahora ejecuta iniciar_jarvis_voz.bat
pause
