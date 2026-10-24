"""
Jarvis por voz — mantén pulsada la tecla º y habla, o di "Hey Pato" y habla.
  1) Mantienes pulsada la tecla º (o dices "Hey Pato") y hablas
  2) Al soltarla, tu voz se convierte en texto        (Vosk, local en tu PC)
  3) El texto se envía a Antigravity CLI (agy) en esta bóveda      (agy -p)
  4) Jarvis te responde en voz alta                    (voz neuronal de Microsoft)
"""
import asyncio
import atexit
import collections
import json
import os
import queue
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import re
import time
import traceback
import unicodedata
import urllib.parse
import urllib.request
import winsound
import zipfile
from datetime import datetime
from pathlib import Path

import keyboard
import numpy as np
import sounddevice as sd
from vosk import KaldiRecognizer, Model as VoskModel, SetLogLevel

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

# ----------------------------- AJUSTES -----------------------------
VAULT = Path(os.environ.get("JARVIS_BOVEDA") or Path(__file__).resolve().parents[1])   # carpeta de la bóveda (raíz del repo)
LOG = Path(__file__).with_name("jarvis_voz.log")

TECLA = 41                     # código de la tecla º (la de debajo de Esc). Se "traga" para no escribir º
MAX_ORDEN_SEG = 60             # duración máxima de una orden
MIN_ORDEN_SEG = 0.5            # menos que esto = pulsación accidental
PREROLL_SEG = 0.5              # audio de ANTES de pulsar que se conserva (para no cortar la 1ª palabra)
ACTIVACION_POR_VOZ = True      # además de la tecla, se puede decir "Hey Pato"
PALABRA_CLAVE = "pato"
GANANCIA_DETECCION = 3         # sube si no te oye desde lejos (máx. recomendado 6)
PREVIAS = ["hey", "ey", "ei", "eh"]   # formas con las que el modelo puede oír "hey"
SILENCIO_SEG = 1.3             # con "Hey Pato": pausa que da por terminada la orden
MAX_ORDEN_VOZ_SEG = 30
COLA_SEG = 0.5                 # se sigue grabando este rato DESPUÉS de soltar (para no cortar la última)

# "vosk-model-small-es-0.42" (~40 MB, rápido) o "vosk-model-es-0.42" (~1,4 GB, mucho más preciso)
VOSK_MODELO = "vosk-model-es-0.42"
VOSK_URL = f"https://alphacephei.com/vosk/models/{VOSK_MODELO}.zip"

# Whisper (faster-whisper, local) transcribe las órdenes mucho mejor que Vosk.
# Vosk se sigue usando para detectar "Hey Pato" y como respaldo si Whisper no está instalado.
USAR_WHISPER = True
WHISPER_MODELO = "small"       # "base" (rápido), "small" (equilibrado) o "medium" (más preciso, más lento)
WHISPER_PISTA = "Órdenes para Jarvis: correo, borrador, calendario, Spotify, Drive, Obsidian, nota, apagar el ordenador."

# Memoria entre órdenes: si la orden anterior fue hace menos de esto, se continúa la misma
# conversación (así "sí, hazlo" sabe a qué te refieres). Si no, se empieza una nueva.
SESION_MIN = 5
ULTIMA_ORDEN = Path(__file__).with_name("ultima_orden.txt")

# Voz de Jarvis. USAR_VOZ_NEURAL=True envía el TEXTO de la respuesta (nunca tu audio)
# al servicio de voz de Microsoft Edge. False = voz local de Windows (más robótica, 100% offline).
USAR_VOZ_NEURAL = True
VOZ = "es-ES-XimenaNeural"    # otras: es-ES-AlvaroNeural,: es-ES-ElviraNeural, es-MX-JorgeNeural, es-AR-TomasNeural
VELOCIDAD = "+5%"
VOLUMEN = "+50%"               # volumen de la voz de Jarvis (máx. "+100%")

# Piper: voz gratis y 100% local (no envía nada a internet). Si USAR_PIPER=True se usa antes
# que la de Microsoft; si falla (no instalado, sin modelo...), se usa la de Microsoft.
# La voz se descarga sola la primera vez. Voces en español (ruta "idioma/region/nombre/calidad"):
#   es/es_ES/davefx/medium   (hombre, España)      es/es_ES/sharvard/medium (hombre/mujer, España)
#   es/es_ES/carlfm/x_low    (hombre, España)      es/es_MX/ald/medium      (hombre, México)
#   es/es_MX/claude/high     (mujer, México)
# Todas (y otros idiomas): https://huggingface.co/rhasspy/piper-voices/tree/main
USAR_PIPER = False
PIPER_VOZ = "es/es_ES/davefx/medium"
PIPER_VELOCIDAD = 1.0          # 1.0 normal; 0.8 más rápido; 1.2 más lento
PIPER_DIR = Path(__file__).with_name("voces_piper")

TIMEOUT_AGY = 300           # segundos máximos por orden

# Ahorro de consumo: cada orden va al modelo más barato que la puede resolver bien.
# flash-lite = charla y órdenes simples; flash = uso normal; pro = informes, análisis y programar.
# Di "modo potente" o "piénsalo bien" en la orden para forzar pro.
ENRUTAR_MODELO = False         # False = modelo por defecto de agy. Si lo activas, pon en MODELO_* los nombres exactos de "agy models"
MODELO_SIMPLE = ""
MODELO_NORMAL = ""
MODELO_POTENTE = ""
PALABRAS_POTENTE = ["informe", "analiza", "analisis", "investiga", "investigacion", "script", "programa",
                    "codigo", "optimiza", "compara", "estrategia", "planifica", "plan de", "modo potente",
                    "piensalo bien", "a fondo", "detallado", "configura", "arregla", "error"]
PALABRAS_SIMPLE = ["hola", "que tal", "gracias", "buenos dias", "buenas noches", "abre", "abreme", "que hora",
                   "que dia", "que tengo hoy", "mi agenda", "chiste", "adios", "vale", "perfecto"]
# Historial: se continúa la conversación como mucho SESION_MIN minutos y MAX_ORDENES_SESION órdenes.
# Al empezar una nueva no se pierde nada: se le pasa un resumen de los últimos mensajes del chat
# y la memoria permanente de la bóveda (MAQUINA/memoria) sigue ahí.
MAX_ORDENES_SESION = 8
CONTEXTO_CHAT_MENSAJES = 6     # mensajes recientes del chat que se pasan al empezar conversación nueva
CONSUMO_DB = Path(__file__).with_name("consumo.db")   # registro de cada orden: modelo, tokens, coste

# agy se ejecuta con --dangerously-skip-permissions (sin pedir permiso por cada herramienta).
# Correo, calendario, Drive y Spotify solo funcionan si añades sus servidores con "agy mcp add" (ver README).
# -------------------------------------------------------------------

SR = 16000
CHUNK = 1280  # 80 ms
pulsada = threading.Event()
activacion_voz = threading.Event()


def log(msg: str) -> None:
    linea = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    if sys.stdout:
        print(linea, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(linea + "\n")


CHAT = VAULT / "MAQUINA" / "chat-jarvis.md"     # conversación por voz, visible en Obsidian


def anotar_chat(quien: str, texto: str) -> None:
    CHAT.parent.mkdir(parents=True, exist_ok=True)
    if not CHAT.exists():
        CHAT.write_text("---\ntipo: chat\ntags: [jarvis, voz]\n---\n# Chat con Jarvis\n", encoding="utf-8")
    ahora = datetime.now()
    with CHAT.open("a", encoding="utf-8") as f:
        f.write(f"\n**{quien}** · {ahora:%d/%m %H:%M}\n{texto}\n")


def pitido(freq: int, ms: int = 120) -> None:
    try:
        winsound.Beep(freq, ms)
    except Exception:
        pass


# ----------------------------- MASCOTA (Pato) -----------------------------
USAR_MASCOTA = True
MASCOTA_SCRIPT = Path(__file__).with_name("mascota_pato.py")
MASCOTA_ESTADO = Path(__file__).with_name("mascota_estado.json")
MASCOTA_CMD = Path(__file__).with_name("mascota_cmd.txt")
SIN_VENTANA = subprocess.CREATE_NO_WINDOW        # que ninguna consola se abra ni moleste


MASCOTA_RESP = Path(__file__).with_name("mascota_respuesta.json")


def mascota_respuesta(texto: str) -> None:
    """Pasa la respuesta completa a la mascota para que la muestre en un bocadillo (con 'Leer más')."""
    if not USAR_MASCOTA:
        return
    try:
        tmp = MASCOTA_RESP.with_suffix(".tmp")
        tmp.write_text(json.dumps({"texto": texto, "hora": time.time()}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, MASCOTA_RESP)
    except Exception:
        pass


def mascota(estado: str, texto: str = "") -> None:
    """Le dice a la mascota qué hacer: reposo, escuchando, pensando, trabajando, hablando, hecho, error."""
    if not USAR_MASCOTA:
        return
    try:
        tmp = MASCOTA_ESTADO.with_suffix(".tmp")
        tmp.write_text(json.dumps({"estado": estado, "texto": texto}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, MASCOTA_ESTADO)
    except Exception:
        pass


def lanzar_mascota() -> None:
    if not USAR_MASCOTA or not MASCOTA_SCRIPT.exists():
        return
    try:
        err = open(MASCOTA_SCRIPT.with_name("mascota.log"), "a", encoding="utf-8")
        subprocess.Popen([sys.executable, str(MASCOTA_SCRIPT)], cwd=str(MASCOTA_SCRIPT.parent),
                         stdin=subprocess.DEVNULL, stdout=err, stderr=err, creationflags=SIN_VENTANA)
    except Exception as e:
        log(f"(no pude lanzar la mascota: {e})")


_ETIQ_MCP = [("Gmail", "Mirando el correo"), ("Calendar", "Mirando tu agenda"), ("Spotify", "Hablando con Spotify"),
             ("Drive", "Buscando en Drive"), ("Docs", "Creando un documento")]
_ETIQ_BASE = {"google_web_search": "Buscando en internet", "web_fetch": "Leyendo una web",
              "read_file": "Revisando tus notas", "read_many_files": "Revisando tus notas",
              "list_directory": "Revisando tus notas", "glob": "Revisando tus notas",
              "search_file_content": "Revisando tus notas", "grep_search": "Revisando tus notas",
              "write_file": "Escribiendo una nota", "replace": "Escribiendo una nota",
              "run_shell_command": "Abriendo algo", "save_memory": "Guardando en memoria"}


def etiqueta_herramienta(nombre: str) -> str:
    for clave, txt in _ETIQ_MCP:
        if clave.lower() in nombre.lower():
            return txt
    return _ETIQ_BASE.get(nombre, "Trabajando…")


# ----------------------------- VOZ DE SALIDA -----------------------------
def _ps(script: str, **env_extra) -> None:
    env = dict(os.environ, **env_extra)
    subprocess.run(["powershell", "-NoProfile", "-Command", script], env=env,
                   creationflags=subprocess.CREATE_NO_WINDOW)


def hablar_windows(texto: str) -> None:
    _ps("Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$s.Speak($env:JARVIS_TEXTO)", JARVIS_TEXTO=texto)


async def _sintetizar(texto: str, ruta: str) -> None:
    import edge_tts
    await edge_tts.Communicate(texto, VOZ, rate=VELOCIDAD, volume=VOLUMEN).save(ruta)


def reproducir_mp3(ruta: Path) -> None:
    _ps("Add-Type -AssemblyName PresentationCore;"
        "$p = New-Object System.Windows.Media.MediaPlayer;"
        "$p.Volume = 1.0; $p.Open([Uri]$env:JARVIS_MP3);"
        "$t = 0; while(-not $p.NaturalDuration.HasTimeSpan -and $t -lt 50){Start-Sleep -Milliseconds 100; $t++};"
        "$p.Play();"
        "Start-Sleep -Milliseconds ([int]$p.NaturalDuration.TimeSpan.TotalMilliseconds + 400);"
        "$p.Close()", JARVIS_MP3=str(ruta))


_piper_cache = {}


def _modelo_piper() -> Path:
    nombre = PIPER_VOZ.rstrip("/").split("/")
    archivo = f"{nombre[1]}-{nombre[2]}-{nombre[3]}.onnx"
    ruta = PIPER_DIR / archivo
    base = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{PIPER_VOZ.strip('/')}/{archivo}"
    PIPER_DIR.mkdir(exist_ok=True)
    for destino, url in ((ruta, base), (ruta.with_suffix(".onnx.json"), base + ".json")):
        if not destino.exists():
            log(f"Descargando voz Piper: {url}")
            tmp = destino.with_suffix(destino.suffix + ".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.replace(destino)
    return ruta


def hablar_piper(texto: str) -> None:
    import wave
    from piper import PiperVoice
    modelo = _modelo_piper()
    voz = _piper_cache.get(modelo)
    if voz is None:
        voz = _piper_cache[modelo] = PiperVoice.load(str(modelo))
    ruta = Path(tempfile.gettempdir()) / "jarvis_tts.wav"
    with wave.open(str(ruta), "wb") as wf:
        if hasattr(voz, "synthesize_wav"):          # piper-tts 1.3 o posterior
            from piper import SynthesisConfig
            voz.synthesize_wav(texto, wf, syn_config=SynthesisConfig(length_scale=PIPER_VELOCIDAD))
        else:                                       # versiones antiguas
            voz.synthesize(texto, wf, length_scale=PIPER_VELOCIDAD)
    winsound.PlaySound(str(ruta), winsound.SND_FILENAME)


def hablar(texto: str) -> None:
    texto = " ".join(texto.split())[:900]
    if not texto:
        return
    if USAR_PIPER:
        try:
            hablar_piper(texto)
            return
        except Exception as e:
            log(f"(voz Piper no disponible: {e}; uso la de Microsoft)")
    if USAR_VOZ_NEURAL:
        try:
            ruta = Path(tempfile.gettempdir()) / "jarvis_tts.mp3"
            asyncio.run(_sintetizar(texto, str(ruta)))
            reproducir_mp3(ruta)
            return
        except Exception as e:
            log(f"(voz neuronal no disponible: {e}; uso la voz de Windows)")
    hablar_windows(texto)


# ----------------------------- VOZ DE ENTRADA -----------------------------
def preparar_vosk() -> VoskModel:
    carpeta = Path(__file__).with_name("modelos")
    destino = carpeta / VOSK_MODELO
    if not destino.exists():
        carpeta.mkdir(exist_ok=True)
        zip_path = carpeta / (VOSK_MODELO + ".zip")
        log(f"Descargando modelo de voz de {VOSK_URL}")
        ultimo = [-10]

        def progreso(bloques, tam, total):
            if total > 0:
                pct = min(100, int(bloques * tam * 100 / total))
                if pct >= ultimo[0] + 10:
                    ultimo[0] = pct
                    log(f"  descargando modelo… {pct}%")

        urllib.request.urlretrieve(VOSK_URL, zip_path, progreso)
        log("Descomprimiendo modelo (puede tardar un par de minutos)…")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(carpeta)
        zip_path.unlink()
    SetLogLevel(-1)
    return VoskModel(str(destino))


class Microfono:
    """Micrófono abierto con un pequeño búfer de ~0,5 s que se va descartando.
    Nada se guarda ni se envía hasta que pulsas la tecla o dices "Hey Pato"."""

    def __init__(self) -> None:
        self.previo = collections.deque(maxlen=max(1, int(PREROLL_SEG * SR / CHUNK)))
        self.niveles = collections.deque(maxlen=40)      # ~3 s de nivel de ruido
        self.cola: "queue.Queue" = queue.Queue(maxsize=300)  # audio para el detector de "Hey Pato"
        self.trozos: list = []
        self.grabando = False
        self.ocupado = False                             # True mientras procesa/habla
        self.stream = sd.InputStream(samplerate=SR, channels=1, dtype="int16",
                                     blocksize=CHUNK, callback=self._cb)
        self.stream.start()

    def _cb(self, indata, frames, tiempo, estado) -> None:
        bloque = indata[:, 0].copy()
        if self.grabando:
            self.trozos.append(bloque)
            return
        self.previo.append(bloque)
        self.niveles.append(float(np.abs(bloque).mean()))
        if ACTIVACION_POR_VOZ and not self.ocupado:
            try:
                self.cola.put_nowait(bloque)
            except queue.Full:
                pass

    def vaciar_cola(self) -> None:
        try:
            while True:
                self.cola.get_nowait()
        except queue.Empty:
            pass

    def grabar_mientras_pulsada(self) -> np.ndarray:
        self.trozos = list(self.previo)       # incluye el medio segundo anterior
        self.grabando = True
        t0 = time.time()
        while pulsada.is_set() and time.time() - t0 < MAX_ORDEN_SEG:
            time.sleep(0.02)
        time.sleep(COLA_SEG)                  # cola tras soltar
        self.grabando = False
        while pulsada.is_set():               # si se alcanzó el máximo, espera a que sueltes
            time.sleep(0.05)
        return np.concatenate(self.trozos) if self.trozos else np.array([], dtype="int16")

    def grabar_por_silencio(self) -> np.ndarray:
        """Tras "Hey Pato": graba hasta que hables y luego hagas una pausa."""
        ruido = float(np.percentile(list(self.niveles), 20)) if self.niveles else 100.0
        umbral = max(250.0, ruido * 3)
        self.trozos = []
        self.grabando = True
        t0, hablando, silencio, vistos = time.time(), False, 0.0, 0
        while time.time() - t0 < MAX_ORDEN_VOZ_SEG:
            time.sleep(CHUNK / SR)
            nuevos, vistos = self.trozos[vistos:], len(self.trozos)
            for b in nuevos:
                if np.abs(b).mean() > umbral:
                    hablando, silencio = True, 0.0
                elif hablando:
                    silencio += CHUNK / SR
            if hablando and silencio >= SILENCIO_SEG:
                break
            if not hablando and time.time() - t0 > 6:    # nadie habló
                break
        self.grabando = False
        trozos = self.trozos[3:]               # descarta el final de "pato" (~0,25 s)
        return np.concatenate(trozos) if (hablando and trozos) else np.array([], dtype="int16")


def vigilar_hey_pato(modelo: VoskModel, micro: Microfono) -> None:
    """Hilo que escucha SOLO la palabra "pato" (gramática cerrada, todo local).
    "Hey Pato" funciona igual: el "hey" previo se ignora, porque el modelo no lo reconoce bien."""
    gramatica = json.dumps([PALABRA_CLAVE, "[unk]"])
    rec = KaldiRecognizer(modelo, SR, gramatica)
    while True:
        try:
            b = micro.cola.get(timeout=0.5)
        except queue.Empty:
            continue
        # amplifica x3 (con tope) para oír mejor desde lejos
        b = np.clip(b.astype(np.int32) * GANANCIA_DETECCION, -32768, 32767).astype(np.int16)
        if rec.AcceptWaveform(b.tobytes()):
            texto = json.loads(rec.Result()).get("text", "")
        else:
            texto = json.loads(rec.PartialResult()).get("partial", "")
        if PALABRA_CLAVE in texto.split():
            log('Palabra de activación detectada ("pato").')
            micro.ocupado = True
            activacion_voz.set()
            rec = KaldiRecognizer(modelo, SR, gramatica)   # reinicia el detector


def preparar_whisper():
    if not USAR_WHISPER:
        return None
    if WhisperModel is None:
        log("(faster-whisper no está instalado; transcribo con Vosk. Ejecuta instalar.bat)")
        return None
    try:
        log(f"Cargando Whisper ({WHISPER_MODELO}); la primera vez se descarga…")
        return WhisperModel(WHISPER_MODELO, device="cpu", compute_type="int8")
    except Exception as e:
        log(f"(no pude cargar Whisper: {e}; transcribo con Vosk)")
        return None


def transcribir(modelo: VoskModel, audio: np.ndarray, whisper=None) -> str:
    pico = int(np.abs(audio).max()) if audio.size else 0
    if 0 < pico < 12000:                      # voz muy baja: súbela (máx. x8)
        audio = np.clip(audio.astype(np.int32) * min(8.0, 16000 / pico), -32768, 32767).astype("int16")
    if whisper is not None:
        try:
            segmentos, _ = whisper.transcribe(audio.astype(np.float32) / 32768.0, language="es",
                                              beam_size=5, vad_filter=True,
                                              initial_prompt=WHISPER_PISTA)
            return " ".join(s.text.strip() for s in segmentos).strip()
        except Exception as e:
            log(f"(Whisper falló: {e}; uso Vosk)")
    rec = KaldiRecognizer(modelo, SR)
    rec.AcceptWaveform(audio.tobytes())
    return json.loads(rec.FinalResult()).get("text", "").strip()


# ----------------------------- GEMINI -----------------------------
def encontrar_agy() -> str:
    ruta = shutil.which("agy")
    if ruta:
        return ruta
    for c in (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Antigravity CLI" / "agy.exe",
              Path.home() / ".local" / "bin" / "agy.exe", Path.home() / ".local" / "bin" / "agy"):
        if c.exists():
            return str(c)
    sys.exit("No encuentro 'agy'. Instálalo con: irm https://antigravity.google/cli/install.ps1 | iex")


def elegir_modelo(orden: str):
    """Elige el modelo más barato adecuado para la orden (reglas sencillas, sin gastar nada)."""
    if not ENRUTAR_MODELO:
        return None
    t = _norm(orden)
    if any(p in t for p in PALABRAS_POTENTE) or len(t.split()) > 40:
        return MODELO_POTENTE
    if len(t.split()) <= 8 or any(t.startswith(p) or p in t for p in PALABRAS_SIMPLE):
        return MODELO_SIMPLE
    return MODELO_NORMAL


def contexto_reciente() -> str:
    """Últimos mensajes del chat (sin la orden actual), para no perder el hilo en una conversación nueva."""
    try:
        bloques = re.split(r"\n(?=\*\*(?:Tú|Jarvis)\*\* · )", CHAT.read_text(encoding="utf-8"))
    except OSError:
        return ""
    bloques = [b.strip() for b in bloques if b.strip().startswith("**")][:-1]   # quita la orden actual
    recientes = [" ".join(b.split())[:300] for b in bloques[-CONTEXTO_CHAT_MENSAJES:]]
    return "\n".join(recientes)


def _sesion():
    """Devuelve (continuar, número de órdenes ya hechas en esta conversación)."""
    if not ULTIMA_ORDEN.exists() or time.time() - ULTIMA_ORDEN.stat().st_mtime >= SESION_MIN * 60:
        return False, 0
    try:
        n = int(ULTIMA_ORDEN.read_text().strip() or 0)
    except ValueError:
        n = 1
    return (n < MAX_ORDENES_SESION), n


def registrar_consumo(orden: str, modelo, nueva: bool, resultado, segundos: float, error: bool, sesion_id=None) -> None:
    """Guarda en consumo.db una fila por orden (para analizar el gasto después)."""
    try:
        r = resultado or {}
        u = r.get("stats") or {}
        modelos = ",".join((u.get("models") or {}).keys()) or (modelo or "defecto")
        with sqlite3.connect(CONSUMO_DB) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS ordenes (
                id INTEGER PRIMARY KEY, fecha TEXT, orden TEXT, modelo_pedido TEXT, modelos_usados TEXT,
                conversacion_nueva INTEGER, turnos INTEGER, tokens_entrada INTEGER, tokens_salida INTEGER,
                tokens_cache_leidos INTEGER, tokens_cache_creados INTEGER, coste_usd REAL,
                segundos REAL, error INTEGER, sesion TEXT)""")
            db.execute("INSERT INTO ordenes (fecha, orden, modelo_pedido, modelos_usados, conversacion_nueva, turnos,"
                       " tokens_entrada, tokens_salida, tokens_cache_leidos, tokens_cache_creados, coste_usd,"
                       " segundos, error, sesion) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (datetime.now().isoformat(timespec="seconds"), orden[:500], modelo or "defecto", modelos,
                        int(nueva), u.get("tool_calls"), u.get("input_tokens"), u.get("output_tokens"),
                        u.get("cached"), None, None, round(segundos, 1), int(error), sesion_id))
    except Exception as e:
        log(f"(no pude registrar el consumo: {e})")


def preguntar_a_agy(agy: str, orden: str) -> str:
    inicio = time.time()
    modelo = elegir_modelo(orden)
    reciente, n_ordenes = _sesion()
    previo = "" if reciente else contexto_reciente()
    prompt = (
        (f"Contexto: últimos mensajes de la conversación por voz (por si la orden se refiere a ellos):\n{previo}\n\n"
         if previo else "") +
        "ORDEN POR VOZ (transcrita automáticamente, puede tener errores; "
        "si es ambigua o peligrosa, pide confirmación en vez de actuar): "
        f"{orden}\n\n"
        "Reglas: si la orden pide un informe, resumen largo o investigación, guárdalo como nota "
        "en MAQUINA/investigacion/ (Markdown con frontmatter) y dime el nombre del archivo. "
        "Puedes buscar en internet, leer y escribir notas de la bóveda y abrir páginas web o programas (con el comando start de Windows); "
        "si tienes conectados correo, calendario, Drive o Spotify, úsalos (en correo solo borradores, nunca enviar). "
        "Si algo requiere un permiso o conexión que no tienes, dímelo claramente. "
        "Responde en 1-3 frases cortas y naturales, aptas para leerse en voz alta, "
        "sin markdown, sin listas y sin rutas largas."
    )
    cmd = [agy, "-p", prompt] + (["--continue"] if reciente else []) + (["--model", modelo] if modelo else []) + [
        "--dangerously-skip-permissions", "--print-timeout", f"{TIMEOUT_AGY}s"]
    log(f"(modelo: {modelo or 'defecto'}; " + (f"continúa, orden {n_ordenes + 1})" if reciente else "conversación nueva)"))

    def _fin(texto: str, ok: bool) -> str:
        if ok:
            ULTIMA_ORDEN.write_text(str(n_ordenes + 1 if reciente else 1))
        registrar_consumo(orden, modelo, not reciente, resultado, time.time() - inicio, not ok, sesion["id"])
        return texto

    proc = subprocess.Popen(cmd, cwd=VAULT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                            creationflags=SIN_VENTANA)
    caducado = {"v": False}
    sesion = {"id": None}

    def _matar():
        caducado["v"] = True
        proc.kill()

    temporizador = threading.Timer(TIMEOUT_AGY, _matar)
    temporizador.start()
    resultado = None
    mascota("pensando", "Pensando…")
    try:
        salida = proc.stdout.read()
    finally:
        temporizador.cancel()
    proc.wait()
    if caducado["v"]:
        return _fin("La orden ha tardado demasiado y la he cancelado.", False)
    texto = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", salida).strip()
    if proc.returncode == 0 and texto:
        return _fin(texto, True)
    log(f"agy devolvió error (código {proc.returncode}): {texto[:500]}")
    return _fin("Ha habido un error al ejecutar la orden. Mira el registro para ver el detalle.", False)


# ----------------------------- MÚSICA (Spotify y cualquier reproductor) -----------------------------
def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return re.sub(r"[^a-z0-9 ]", "", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()


def manejar_musica(orden: str):
    """Órdenes cortas de música: se ejecutan al instante con las teclas multimedia de Windows.
    Devuelve la frase de respuesta, o None si la orden no es de este tipo."""
    t = _norm(orden)
    n = len(t.split())
    acciones = [
        (r"^(pausa|pausar|pon pausa|para|parar|detén|deten|reanuda|reanudar|continua|continuar|play)( la)?( musica| cancion)?$",
         "play/pause media", "Hecho."),
        (r"^(para|pausa|pausar|deten|detener|quita|apaga) (la )?(musica|cancion|spotify)$", "play/pause media", "Hecho."),
        (r"^(siguiente|salta|saltar|pasa|proxima|next)( cancion| tema| la cancion)?$", "next track", "Siguiente."),
        (r"^(anterior|vuelve|volver|atras|previous)( cancion| tema| a la anterior)?$", "previous track", "Anterior."),
        (r"^(sube|subir|mas alto|aumenta)( el)?( volumen)?$", "volume up", "Volumen arriba."),
        (r"^(baja|bajar|mas bajo|reduce)( el)?( volumen)?$", "volume down", "Volumen abajo."),
        (r"^(silencio|silencia|mutea|mute|quita el sonido)$", "volume mute", "Silenciado."),
    ]
    if n <= 5:
        if re.match(r"^(oculta|esconde|quita|guarda|apaga|cierra)( a| la| el)?( mascota| pato| patito)$", t):
            MASCOTA_CMD.write_text("ocultar")
            return "Vale, me escondo."
        if re.match(r"^(muestra|saca|ensena|ensename|pon|activa|aparece|vuelve)( a| la| el)?( mascota| pato| patito)$", t):
            MASCOTA_CMD.write_text("mostrar")
            return "¡Cuac! Aquí estoy."
    if n <= 6:
        for patron, tecla, respuesta in acciones:
            if re.match(patron, t):
                veces = 5 if tecla in ("volume up", "volume down") else 1
                for _ in range(veces):
                    keyboard.send(tecla)
                return respuesta
    # "pon / busca / reproduce <algo> en spotify" -> abre Spotify con esa búsqueda
    m = re.match(r"^(pon|ponme|busca|buscame|reproduce|reproduceme|escuchar|quiero escuchar) (.+?)( en spotify)?$", t)
    if m and ("spotify" in t or "musica" in t or "cancion" in t):
        consulta = re.sub(r"^(musica de|la musica de|la cancion|cancion|musica) ", "", m.group(2)).strip()
        try:
            os.startfile("spotify:search:" + urllib.parse.quote(consulta))
            return f"He abierto Spotify con la búsqueda {consulta}. Dale al play."
        except Exception as e:
            log(f"(no pude abrir Spotify: {e})")
            return None
    return manejar_local(t)


# Órdenes sencillas que se resuelven en el PC sin gastar consumo de Gemini
WEBS = {"youtube": "https://www.youtube.com", "gmail": "https://mail.google.com", "correo": "https://mail.google.com",
        "calendario": "https://calendar.google.com", "agenda": "https://calendar.google.com",
        "drive": "https://drive.google.com", "google": "https://www.google.com", "whatsapp": "https://web.whatsapp.com",
        "netflix": "https://www.netflix.com", "twitch": "https://www.twitch.tv", "chatgpt": "https://chatgpt.com",
        "gemini": "https://gemini.google.com", "spotify": "spotify:", "obsidian": "obsidian://open"}


def manejar_local(t: str):
    if len(t.split()) > 6:
        return None
    m = re.match(r"^(abre|abreme|pon|ponme|entra en|ve a)( el| la| mi)? (\w+)$", t)
    if m and m.group(3) in WEBS:
        try:
            os.startfile(WEBS[m.group(3)])
            return "Abierto."
        except Exception as e:
            log(f"(no pude abrir {m.group(3)}: {e})")
            return None
    if re.match(r"^(que hora es|dime la hora|hora)$", t):
        return f"Son las {datetime.now():%H:%M}."
    if re.match(r"^(cuanto|que) (he gastado|consumo|llevo gastado|has gastado)( hoy)?$", t):
        return resumen_consumo_hoy()
    return None


def resumen_consumo_hoy() -> str:
    if not CONSUMO_DB.exists():
        return "Todavía no tengo datos de consumo."
    with sqlite3.connect(CONSUMO_DB) as db:
        n, coste, entrada = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(coste_usd),0), COALESCE(SUM(tokens_entrada+tokens_cache_leidos),0)"
            " FROM ordenes WHERE fecha >= ?", (f"{datetime.now():%Y-%m-%d}",)).fetchone()
    return (f"Hoy llevas {n} órdenes, unos {entrada // 1000} mil tokens de entrada "
            f"y un coste equivalente de {coste:.2f} dólares.")

# ----------------------------- PRINCIPAL -----------------------------
PID_FILE = Path(__file__).with_name("jarvis.pid")


_MUTEX = None


def instancia_unica() -> bool:
    """Impide que haya dos copias de Jarvis a la vez (se pisarían micrófono y tecla)."""
    global _MUTEX
    import ctypes
    k32 = ctypes.windll.kernel32
    _MUTEX = k32.CreateMutexW(None, False, "Local\\JarvisVozPato")
    return k32.GetLastError() != 183          # 183 = ya existía otra copia


def main() -> None:
    if not instancia_unica():
        log("Ya hay otra copia de Jarvis en marcha; esta se cierra.")
        return
    PID_FILE.write_text(str(os.getpid()))
    atexit.register(lambda: PID_FILE.unlink(missing_ok=True))
    mascota("pensando", "Despertando…")
    lanzar_mascota()
    pitido(500, 100)                      # 1er pitido: arrancando (cargar el modelo tarda ~30 s)
    agy = encontrar_agy()
    log(f"Bóveda: {VAULT} (proceso {os.getpid()})")
    modelo = preparar_vosk()
    whisper = preparar_whisper()
    micro = Microfono()

    def on_tecla(e):
        (pulsada.set if e.event_type == "down" else pulsada.clear)()

    keyboard.hook_key(TECLA, on_tecla, suppress=True)
    if ACTIVACION_POR_VOZ:
        threading.Thread(target=vigilar_hey_pato, args=(modelo, micro), daemon=True).start()
    log('Listo. Mantén pulsada la tecla º y habla, o di "Hey Pato" y habla. Ctrl+C para salir.'
        if ACTIVACION_POR_VOZ else "Listo. Mantén pulsada la tecla º, habla y suéltala. Ctrl+C para salir.")
    pitido(660)                           # 2º pitido: listo
    pitido(880, 150)
    mascota("hecho", "¡Listo!")

    while True:
        micro.ocupado = False
        activacion_voz.clear()
        micro.vaciar_cola()
        while not pulsada.is_set() and not activacion_voz.wait(0.15):   # con timeout: Ctrl+C funciona
            pass
        micro.ocupado = True
        pitido(880, 80)
        mascota("escuchando")
        if pulsada.is_set():
            audio = micro.grabar_mientras_pulsada()
            minimo = SR * MIN_ORDEN_SEG
        else:
            log('"Hey Pato" detectado, te escucho…')
            audio = micro.grabar_por_silencio()
            minimo = SR * 0.3
        if audio.size < minimo:
            log("No he captado ninguna orden.")
            pitido(400)
            mascota("reposo")
            continue
        pitido(600, 80)
        mascota("pensando", "Entendiendo…")
        orden = transcribir(modelo, audio, whisper)
        if len(orden) < 3:
            log("No he entendido nada.")
            pitido(400)
            mascota("error", "No te he entendido")
            continue
        log(f"Orden: {orden}")
        anotar_chat("Tú", orden)
        respuesta = manejar_musica(orden)
        if respuesta is None:
            mascota("pensando", "Pensando…")
            try:
                respuesta = preguntar_a_agy(agy, orden)
            except subprocess.TimeoutExpired:
                respuesta = "La orden ha tardado demasiado y la he cancelado."
        log(f"Respuesta: {respuesta}")
        anotar_chat("Jarvis", respuesta)
        mascota_respuesta(respuesta)
        fallo = respuesta.startswith("Ha habido un error") or "he cancelado" in respuesta
        mascota("hablando")
        hablar(respuesta)
        mascota("error" if fallo else "hecho")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Jarvis por voz detenido.")
    except Exception:
        log("ERROR: " + traceback.format_exc())
        pitido(300, 500)
