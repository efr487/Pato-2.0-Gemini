# Vuelve a mostrar a Pato (o lo lanza si no esta abierto). Sin consola.
import subprocess, sys
from pathlib import Path
AQUI = Path(__file__).resolve().parent
(AQUI / "mascota_cmd.txt").write_text("mostrar", encoding="utf-8")
try:
    out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Process -Filter \"name='pythonw.exe'\").CommandLine"],
                         capture_output=True, text=True, creationflags=0x08000000).stdout
except Exception:
    out = ""
if "mascota_pato.py" not in out:
    subprocess.Popen([sys.executable, str(AQUI / "mascota_pato.py")], cwd=str(AQUI),
                     creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
