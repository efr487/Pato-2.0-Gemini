"""Pulsa teclas multimedia de Windows para que Jarvis controle la música.

Uso: python multimedia.py <play|pausa|siguiente|anterior|stop|subir|bajar|silencio>
"""
import ctypes
import sys

TECLAS = {
    "play": 0xB3,       # reproducir/pausar (alterna)
    "pausa": 0xB3,
    "siguiente": 0xB0,
    "anterior": 0xB1,
    "stop": 0xB2,
    "subir": 0xAF,
    "bajar": 0xAE,
    "silencio": 0xAD,
}

KEYEVENTF_EXTENDEDKEY = 0x1
KEYEVENTF_KEYUP = 0x2


def pulsar(vk):
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
    user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


if __name__ == "__main__":
    accion = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if accion not in TECLAS:
        print("Acción no válida. Usa: " + ", ".join(TECLAS))
        sys.exit(1)
    pulsar(TECLAS[accion])
    print("OK: " + accion)
