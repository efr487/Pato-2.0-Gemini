"""
Mascota PATO — un patito que vive en la esquina de tu pantalla y te cuenta qué hace Jarvis.

  reposo      respira, parpadea
  escuchando  ojos grandes y ondas de sonido
  pensando    nube de pensamiento con puntitos
  trabajando  casco, portátil y tecleando (con el nombre de la tarea debajo)
  hablando    abre y cierra el pico
  hecho       saltito de alegría
  error       ¡ups!

Controles
  · Arrástralo con el ratón para moverlo (recuerda dónde lo dejas).
  · Clic derecho: ocultar, tamaño, volver a la esquina, cerrar.
  · Ctrl+Alt+P: ocultar / mostrar.
  · Por voz: "oculta la mascota" / "muestra la mascota".
  · Doble clic: saltito.

Jarvis le habla escribiendo `mascota_estado.json`. Se cierra solo cuando Jarvis se apaga.
Para verlo sin Jarvis:  pythonw mascota_pato.py --demo
"""
import ctypes
import json
import math
import os
import random
import sys
import time
from pathlib import Path

try:
    import tkinter as tk
except ImportError:          # permite importar el dibujo sin tkinter (pruebas)
    tk = None

AQUI = Path(__file__).resolve().parent
ESTADO = AQUI / "mascota_estado.json"
CMD = AQUI / "mascota_cmd.txt"
RESP = AQUI / "mascota_respuesta.json"
CONF = AQUI / "mascota_config.json"
PID_FILE = AQUI / "jarvis.pid"

KEY = "#010203"                      # color que Windows hace transparente
BASE_W, BASE_H = 190, 236
HOTKEY = "ctrl+alt+p"

AMARILLO = "#FFD84A"
AMARILLO_2 = "#F6C233"
BORDE = "#D69A1C"
VIENTRE = "#FFF1AE"
PICO = "#FF9B3D"
PICO_OSC = "#E5701A"
MEJILLA = "#FF9DB0"
OJO = "#2A2330"
AZUL = "#5BB0FF"
VERDE = "#47C98A"
AMBAR = "#FFB020"
ROJO = "#F0524F"
GRIS = "#2B2F3E"

COLOR_ESTADO = {"escuchando": AZUL, "pensando": AMBAR, "trabajando": VERDE,
                "hablando": AZUL, "hecho": VERDE, "error": ROJO}
TEXTO_ESTADO = {"escuchando": "Te escucho…", "pensando": "Pensando…", "hablando": "",
                "hecho": "¡Listo!", "error": "Ups…"}


# ============================== DIBUJO ==============================
class Pato:
    """Dibuja el pato en cualquier objeto con la API de tkinter.Canvas."""

    def __init__(self, canvas, escala: float = 1.0):
        self.c = canvas
        self.S = escala

    # --- utilidades de dibujo (todo en coordenadas base, se escala aquí) ---
    def _f(self, pts):
        out = []
        for i, v in enumerate(pts):
            out.append(v * self.S)
        return out

    def ov(self, x0, y0, x1, y1, **kw):
        kw = self._kw(kw)
        return self.c.create_oval(*self._f((x0, y0, x1, y1)), **kw)

    def poly(self, pts, **kw):
        flat = [v for p in pts for v in p]
        return self.c.create_polygon(*self._f(flat), **self._kw(kw))

    def ln(self, pts, **kw):
        flat = [v for p in pts for v in p]
        return self.c.create_line(*self._f(flat), **self._kw(kw))

    def arc(self, x0, y0, x1, y1, **kw):
        return self.c.create_arc(*self._f((x0, y0, x1, y1)), **self._kw(kw))

    def rect(self, x0, y0, x1, y1, **kw):
        return self.c.create_rectangle(*self._f((x0, y0, x1, y1)), **self._kw(kw))

    def _kw(self, kw):
        if "width" in kw:
            kw["width"] = max(1, round(kw["width"] * self.S))
        return kw

    def pastilla(self, cx, cy, w, h, **kw):
        """Rectángulo redondeado (cápsula)."""
        r = h / 2
        x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
        self.ov(x0, y0, x0 + 2 * r, y1, **kw)
        self.ov(x1 - 2 * r, y0, x1, y1, **kw)
        kw2 = dict(kw)
        kw2["outline"] = kw.get("fill", "")
        self.rect(x0 + r, y0, x1 - r, y1, **kw2)

    def engranaje(self, cx, cy, r, ang, color):
        dientes = 8
        pts = []
        for i in range(dientes * 2):
            a = ang + i * math.pi / dientes
            rr = r if i % 2 == 0 else r * 0.74
            a1, a2 = a - math.pi / (dientes * 2.6), a + math.pi / (dientes * 2.6)
            pts += [(cx + rr * math.cos(a1), cy + rr * math.sin(a1)),
                    (cx + rr * math.cos(a2), cy + rr * math.sin(a2))]
        self.poly(pts, fill=color, outline="")
        self.ov(cx - r * 0.35, cy - r * 0.35, cx + r * 0.35, cy + r * 0.35, fill=KEY, outline="")

    def estrella(self, cx, cy, r, ang, color):
        pts = []
        for i in range(8):
            a = ang + i * math.pi / 4
            rr = r if i % 2 == 0 else r * 0.32
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        self.poly(pts, fill=color, outline="")

    # --- un fotograma ---
    def frame(self, t: float, estado: str, texto: str = "", t_estado: float = 0.0):
        c = self.c
        c.delete("all")
        OY = 38                               # margen superior para nubes y burbujas
        dx = dy = 0.0
        if estado == "reposo":
            dy = math.sin(t * 2.0) * 2.0
        elif estado == "escuchando":
            dy = math.sin(t * 3.2) * 1.6
        elif estado == "pensando":
            dy = math.sin(t * 1.7) * 2.0
            dx = math.sin(t * 0.9) * 1.5
        elif estado == "trabajando":
            dy = math.sin(t * 17) * 0.8
        elif estado == "hablando":
            dy = math.sin(t * 10) * 1.6
        elif estado == "hecho":
            k = max(0.0, 1 - t_estado / 2.4)
            dy = -abs(math.sin(t_estado * 7.5)) * 18 * k
        elif estado == "error":
            dx = math.sin(t * 34) * 1.4 if t_estado < 0.7 else 0

        # sombra en el suelo
        suelo = OY + 170
        sw = 44 + dy * 0.5
        self.ov(95 - sw, suelo - 5, 95 + sw, suelo + 5, fill="#6F7480", outline="")

        if getattr(self, "cola", False) and estado != "pensando":     # bolitas que salen hacia el bocadillo
            self.ov(128, 54, 134, 60, fill="#FFFFFF", outline="#B8BECC", width=1)
            self.ov(136, 44, 146, 54, fill="#FFFFFF", outline="#B8BECC", width=1)

        def Y(v):
            return v + OY + dy

        def X(v):
            return v + dx

        # patas
        pata_dy = dy * 0.25
        for px in (64, 104):
            self.ov(X(px), suelo - 14 + pata_dy, X(px + 24), suelo - 2 + pata_dy,
                    fill=PICO, outline=PICO_OSC, width=1)

        # cuerpo + vientre
        self.ov(X(50), Y(92), X(140), Y(168), fill=AMARILLO, outline=BORDE, width=2)
        self.ov(X(68), Y(112), X(122), Y(162), fill=VIENTRE, outline="")

        # alas
        ala_i = ala_d = 0.0
        if estado == "trabajando":
            ala_i = math.sin(t * 16) * 5
            ala_d = -math.sin(t * 16) * 5
        elif estado == "hablando":
            ala_d = math.sin(t * 8) * 3
        elif estado == "hecho":
            ala_i = -14 * max(0.0, 1 - t_estado / 2.4)
            ala_d = -14 * max(0.0, 1 - t_estado / 2.4)
        elif estado == "reposo" and (t % 11) > 9.4:          # saludo ocasional
            ala_d = -abs(math.sin(t * 9)) * 12
        if estado != "trabajando":
            self.ov(X(40), Y(110 + ala_i), X(68), Y(148 + ala_i), fill=AMARILLO_2, outline=BORDE, width=2)
            self.ov(X(122), Y(110 + ala_d), X(150), Y(148 + ala_d), fill=AMARILLO_2, outline=BORDE, width=2)

        # portátil (trabajando)
        if estado == "trabajando":
            self.rect(X(52), Y(118), X(138), Y(166), fill="#3A3F4D", outline="#23262F", width=2)
            self.rect(X(57), Y(123), X(133), Y(160), fill="#BFE7FF", outline="")
            for i in range(5):                                  # líneas de "código" que avanzan
                off = (t * 40 + i * 17) % 30
                ancho = 22 + ((i * 29) % 34)
                yy = Y(126 + i * 7)
                if 123 < 126 + i * 7 < 156:
                    self.rect(X(62), yy, X(62 + min(ancho, 66)), yy + 3, fill=VERDE if i % 2 else AZUL, outline="")
            self.poly([(X(44), Y(166)), (X(146), Y(166)), (X(154), Y(175)), (X(36), Y(175))],
                      fill="#AEB4C2", outline="#7C8294", width=1)
            self.ov(X(56), Y(158 + ala_i), X(78), Y(174 + ala_i), fill=AMARILLO_2, outline=BORDE, width=2)
            self.ov(X(112), Y(158 + ala_d), X(134), Y(174 + ala_d), fill=AMARILLO_2, outline=BORDE, width=2)

        # cabeza
        self.ov(X(38), Y(26), X(152), Y(112), fill=AMARILLO, outline=BORDE, width=2)
        # mechón
        self.ln([(X(90), Y(28)), (X(86), Y(14)), (X(96), Y(8))], fill=BORDE, width=3, smooth=True)
        self.ln([(X(97), Y(28)), (X(100), Y(15)), (X(108), Y(12))], fill=BORDE, width=3, smooth=True)

        # casco de obra
        if estado == "trabajando":
            self.arc(X(48), Y(6), X(142), Y(62), start=0, extent=180, style="chord",
                     fill="#FF7B3A", outline="#C9531C", width=2)
            self.rect(X(42), Y(33), X(148), Y(41), fill="#FF7B3A", outline="#C9531C", width=2)
            self.rect(X(90), Y(8), X(100), Y(33), fill="#FFC15A", outline="")

        # mejillas
        self.ov(X(52), Y(78), X(70), Y(91), fill=MEJILLA, outline="")
        self.ov(X(120), Y(78), X(138), Y(91), fill=MEJILLA, outline="")

        # ojos
        ojos = [(72, 64), (118, 64)]
        parpadeo = (t % 3.6) > 3.45 and estado in ("reposo", "hablando", "pensando")
        mirar = (0.0, 0.0)
        rx, ry = 9, 10.5
        if estado == "reposo":
            fase = t % 9
            if 5 < fase < 6.2:
                mirar = (-3.5, 0)
            elif 6.6 < fase < 7.8:
                mirar = (3.5, 0)
        elif estado == "pensando":
            mirar = (3.6, -4.4)
        elif estado == "trabajando":
            mirar = (0, 4.2)
        elif estado == "escuchando":
            rx, ry = 10.5, 12.5
        for ex, ey in ojos:
            ex, ey = X(ex), Y(ey)
            if estado == "hecho":
                self.arc(ex - 9, ey - 6, ex + 9, ey + 12, start=20, extent=140, style="arc", outline=OJO, width=3)
            elif estado == "error":
                self.ln([(ex - 6, ey - 6), (ex + 6, ey + 6)], fill=OJO, width=3, capstyle="round")
                self.ln([(ex + 6, ey - 6), (ex - 6, ey + 6)], fill=OJO, width=3, capstyle="round")
            elif parpadeo:
                self.ln([(ex - 8, ey + 1), (ex + 8, ey + 1)], fill=OJO, width=3, capstyle="round")
            else:
                self.ov(ex - rx, ey - ry, ex + rx, ey + ry, fill="#FFFFFF", outline=OJO, width=1)
                px, py = ex + mirar[0], ey + mirar[1]
                self.ov(px - 5.4, py - 6, px + 5.4, py + 6, fill=OJO, outline="")
                self.ov(px - 3.2, py - 4.8, px - 0.4, py - 2, fill="#FFFFFF", outline="")

        # pico
        abre = 0.0
        if estado == "hablando":
            abre = abs(math.sin(t * 12)) * 8
        elif estado == "hecho":
            abre = 3.0
        elif estado == "pensando":
            abre = 2.0 + math.sin(t * 2) * 1.0
        elif estado == "error":
            abre = 4.0
        self.ov(X(81), Y(84 + abre), X(109), Y(95 + abre), fill=PICO_OSC, outline="")
        if abre > 1.5:
            self.ov(X(84), Y(83), X(106), Y(86 + abre), fill="#5A1F18", outline="")
        self.ov(X(77), Y(73), X(113), Y(91), fill=PICO, outline=PICO_OSC, width=1)
        self.ov(X(84), Y(76), X(98), Y(81), fill="#FFC98F", outline="")

        # ---------- extras de cada estado ----------
        if estado == "escuchando":
            for k in range(3):
                ph = (t * 1.8 + k * 0.33) % 1.0
                r = 8 + ph * 22
                col = AZUL if ph < 0.7 else "#BBD9FF"
                self.arc(X(40) - r, Y(70) - r, X(40) + r, Y(70) + r, start=130, extent=100,
                         style="arc", outline=col, width=3)
                self.arc(X(150) - r, Y(70) - r, X(150) + r, Y(70) + r, start=-50, extent=100,
                         style="arc", outline=col, width=3)

        elif estado == "pensando":
            self.ov(128, 54, 134, 60, fill="#FFFFFF", outline="#B8BECC", width=1)
            self.ov(136, 44, 146, 54, fill="#FFFFFF", outline="#B8BECC", width=1)
            for (a, b, c2, d) in [(112, 6, 154, 38), (140, 4, 184, 38), (124, 14, 172, 44)]:
                self.ov(a, b, c2, d, fill="#FFFFFF", outline="#B8BECC", width=1)
            for (a, b, c2, d) in [(114, 8, 152, 36), (142, 6, 182, 36), (126, 16, 170, 42)]:
                self.ov(a, b, c2, d, fill="#FFFFFF", outline="", width=0)
            act = int(t * 2.6) % 3
            for i, cx in enumerate((131, 148, 165)):
                r = 4.6 if i == act else 3.0
                self.ov(cx - r, 27 - r, cx + r, 27 + r, fill=AMBAR if i == act else "#9AA1B2", outline="")

        elif estado == "trabajando":
            self.engranaje(158, 54, 15, t * 1.8, "#8D95A8")
            self.engranaje(137, 36, 9, -t * 2.9 + 0.4, "#B6BDCC")
            if int(t * 1.2) % 2 == 0:                    # gota de esfuerzo
                self.poly([(X(147), Y(40)), (X(142), Y(52)), (X(152), Y(52))], fill="#8FD0FF", outline="")
                self.ov(X(141.5), Y(47), X(152.5), Y(57), fill="#8FD0FF", outline="")

        elif estado == "hablando":
            for k in range(2):
                ph = (t * 2.2 + k * 0.5) % 1.0
                r = 8 + ph * 16
                self.arc(X(113) - r, Y(86) - r, X(113) + r, Y(86) + r, start=-40, extent=80,
                         style="arc", outline=AZUL if ph < 0.7 else "#BBD9FF", width=3)

        elif estado == "hecho":
            k = max(0.0, 1 - t_estado / 2.4)
            if k > 0:
                for i, (sx, sy, rr) in enumerate([(26, 40, 9), (166, 52, 11), (150, 14, 7), (34, 96, 6)]):
                    pulso = 0.6 + 0.4 * math.sin(t * 8 + i * 1.7)
                    self.estrella(sx, sy + 8, rr * pulso * (0.4 + 0.6 * k), t * 1.5 + i,
                                  "#FFD21F" if i % 2 == 0 else "#FF8FB1")

        elif estado == "error":
            self.ov(150, 6, 180, 36, fill=ROJO, outline="#B3302E", width=2)
            self.rect(163.5, 12, 166.5, 26, fill="#FFFFFF", outline="")
            self.ov(163, 28, 167, 32, fill="#FFFFFF", outline="")
            self.poly([(X(46), Y(50)), (X(41), Y(62)), (X(51), Y(62))], fill="#8FD0FF", outline="")
            self.ov(X(40.5), Y(57), X(51.5), Y(67), fill="#8FD0FF", outline="")

        # ---------- rótulo ----------
        if not texto:
            texto = TEXTO_ESTADO.get(estado, "")
        if texto:
            texto = texto[:30]
            ancho = len(texto) * 6.9 + 34
            cy = BASE_H - 14
            self.pastilla(95, cy, ancho, 22, fill=GRIS, outline="")
            self.ov(95 - ancho / 2 + 8, cy - 4, 95 - ancho / 2 + 16, cy + 4,
                    fill=COLOR_ESTADO.get(estado, AZUL), outline="")
            self.c.create_text((95 + 6) * self.S, cy * self.S, text=texto, fill="#FFFFFF",
                               font=("Segoe UI", max(7, round(9 * self.S)), "bold"))


# ============================== SISTEMA ==============================
def pid_vivo(pid: int) -> bool:
    try:
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        code = ctypes.c_ulong()
        k32.GetExitCodeProcess(h, ctypes.byref(code))
        k32.CloseHandle(h)
        return code.value == 259
    except Exception:
        return True


def jarvis_vivo() -> bool:
    try:
        return pid_vivo(int(PID_FILE.read_text().strip()))
    except Exception:
        return False


def cargar_conf() -> dict:
    try:
        return json.loads(CONF.read_text(encoding="utf-8"))
    except Exception:
        return {}


def guardar_conf(d: dict) -> None:
    try:
        CONF.write_text(json.dumps(d), encoding="utf-8")
    except Exception:
        pass


def area_trabajo():
    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
    r = RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)
    return r.l, r.t, r.r, r.b


def escritorio_virtual():
    g = ctypes.windll.user32.GetSystemMetrics
    return g(76), g(77), g(76) + g(78), g(77) + g(79)


def main(demo: bool = False) -> None:
    if tk is None:
        sys.exit("Falta tkinter")
    k32 = ctypes.windll.kernel32
    if not demo:
        k32.CreateMutexW(None, False, "Local\\JarvisMascotaPato")
        if k32.GetLastError() == 183:
            return
        if not jarvis_vivo():
            return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    dpi = 1.0
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        pass

    conf = cargar_conf()
    escala = float(conf.get("escala", 1.0))
    oculta = bool(conf.get("oculta", False))

    root = tk.Tk()
    root.title("Pato")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg=KEY)
    root.attributes("-transparentcolor", KEY)
    canvas = tk.Canvas(root, bg=KEY, highlightthickness=0, bd=0)
    canvas.pack()
    pato = Pato(canvas, escala * dpi)

    def tam():
        return int(BASE_W * pato.S), int(BASE_H * pato.S)

    def poner_tam():
        w, h = tam()
        canvas.config(width=w, height=h)

    def esquina():
        l, t, r, b = area_trabajo()
        w, h = tam()
        return r - w - int(12 * dpi), b - h - int(8 * dpi)

    def ajustar(x, y):
        vl, vt, vr, vb = escritorio_virtual()
        w, h = tam()
        return max(vl - w // 2, min(x, vr - w // 2)), max(vt, min(y, vb - h // 2))

    poner_tam()
    x, y = conf.get("x"), conf.get("y")
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    if x is None or y is None or not (0 <= int(x) < sw - 40 and 0 <= int(y) < sh - 40):
        x, y = esquina()
    x, y = ajustar(int(x), int(y))
    root.geometry(f"+{x}+{y}")
    root.update_idletasks()

    def sin_foco():
        try:
            u = ctypes.windll.user32
            wid = root.winfo_id()
            u.GetAncestor.restype = ctypes.c_void_p
            u.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            u.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
            u.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
            hwnd = u.GetAncestor(wid, 2) or wid
            ex = u.GetWindowLongW(hwnd, -20)
            u.SetWindowLongW(hwnd, -20, ex | 0x08000000)   # no roba el foco
        except Exception:
            pass

    sin_foco()
    if oculta:
        root.withdraw()

    # ---------- bocadillo con la respuesta + "Leer más" ----------
    import tkinter.font as tkfont
    burb = {"win": None, "full": None, "texto": "", "hasta": 0.0}

    def sin_foco_w(w):
        try:
            u = ctypes.windll.user32
            u.GetAncestor.restype = ctypes.c_void_p
            u.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            u.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
            u.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
            hwnd = u.GetAncestor(w.winfo_id(), 2) or w.winfo_id()
            u.SetWindowLongW(hwnd, -20, u.GetWindowLongW(hwnd, -20) | 0x08000000)
        except Exception:
            pass

    def resumen(t, n=150):
        t = " ".join(t.split())
        if len(t) <= n:
            return t, False
        corte = t[:n].rsplit(" ", 1)[0]
        return corte + "…", True

    def cerrar_burbuja():
        if burb["win"] is not None:
            try:
                burb["win"].destroy()
            except Exception:
                pass
            burb["win"] = None

    def ver_completo():
        if not burb["texto"]:
            return
        try:
            if burb["full"] is not None and burb["full"].winfo_exists():
                burb["full"].lift()
                return
        except Exception:
            pass
        v = tk.Toplevel(root)
        burb["full"] = v
        v.title("Pato dice…")
        v.attributes("-topmost", True)
        v.configure(bg="#FFF8E1")
        ancho, alto = int(520 * dpi), int(360 * dpi)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        v.geometry(f"{ancho}x{alto}+{max(0, sw - ancho - int(40 * dpi))}+{max(0, sh - alto - int(110 * dpi))}")
        barra = tk.Frame(v, bg="#FFF8E1")
        barra.pack(side="bottom", fill="x", padx=10, pady=8)

        def copiar():
            v.clipboard_clear()
            v.clipboard_append(burb["texto"])

        tk.Button(barra, text="Copiar", command=copiar, relief="flat", bg="#E9ECF3", padx=12).pack(side="left")
        tk.Button(barra, text="Cerrar", command=v.destroy, relief="flat", bg="#EDE3C4", padx=12).pack(side="right")
        cuerpo = tk.Frame(v, bg="#FFF8E1")
        cuerpo.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 0))
        sb = tk.Scrollbar(cuerpo)
        sb.pack(side="right", fill="y")
        tx = tk.Text(cuerpo, wrap="word", font=("Segoe UI", 11), bg="#FFFDF5", fg="#2A2330", relief="flat",
                     padx=10, pady=8, yscrollcommand=sb.set)
        tx.pack(side="left", fill="both", expand=True)
        sb.config(command=tx.yview)
        tx.insert("1.0", burb["texto"])
        tx.config(state="disabled")

    def colocar_burbuja():
        w = burb["win"]
        if w is None:
            return
        try:
            w.update_idletasks()
            ww, wh = w.winfo_reqwidth(), w.winfo_reqheight()
            sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
            # esquina inferior izquierda del bocadillo justo encima de las bolitas blancas
            x = root.winfo_x() + int(122 * pato.S)
            y = root.winfo_y() + int(42 * pato.S) - wh
            x = max(0, min(x, sw - ww - 4))
            y = max(0, y)
            w.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def mostrar_burbuja(texto):
        cerrar_burbuja()
        burb["texto"] = texto
        if oculta or not texto.strip():
            return
        corto, hay_mas = resumen(texto)
        w = tk.Toplevel(root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=KEY)
        w.attributes("-transparentcolor", KEY)
        lienzo = tk.Canvas(w, bg=KEY, highlightthickness=0, bd=0)
        lienzo.pack()
        dentro = tk.Frame(lienzo, bg="#FFFFFF")
        tk.Label(dentro, text=corto, wraplength=int(300 * dpi), justify="left", anchor="w", bg="#FFFFFF",
                 fg="#2A2330", font=("Segoe UI", 10)).pack(padx=6, pady=(2, 4), anchor="w")
        fila = tk.Frame(dentro, bg="#FFFFFF")
        fila.pack(fill="x", padx=4, pady=(0, 2))
        tk.Button(fila, text="Leer más", command=ver_completo, relief="flat", bg="#E9ECF3", activebackground="#D6DBE7", fg="#2A2330", activeforeground="#2A2330",
                  font=("Segoe UI", 8, "bold"), padx=8, pady=0, cursor="hand2").pack(side="left")
        tk.Button(fila, text="✕", command=cerrar_burbuja, relief="flat", bg="#E9ECF3", activebackground="#D6DBE7", fg="#2A2330", font=("Segoe UI", 8),
                  padx=6, pady=0, cursor="hand2").pack(side="right")
        dentro.update_idletasks()
        m = int(12 * dpi)
        W, H = dentro.winfo_reqwidth() + 2 * m, dentro.winfo_reqheight() + 2 * m
        lienzo.config(width=W, height=H)
        r = int(16 * dpi)
        x0, y0, x1, y1 = 2, 2, W - 2, H - 2
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
               x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        lienzo.create_polygon(pts, smooth=True, fill="#FFFFFF", outline="#B8BECC", width=2)
        lienzo.create_window(W // 2, H // 2, window=dentro)
        burb["win"] = w
        burb["hasta"] = time.time() + 15
        w.update_idletasks()
        sin_foco_w(w)
        colocar_burbuja()

    resp_mt = {"v": 0.0}
    try:
        resp_mt["v"] = RESP.stat().st_mtime        # ignora la respuesta antigua al arrancar
    except Exception:
        pass

    est = {"estado": "reposo", "texto": "", "desde": time.time(), "mtime": 0.0}
    flags = {"alternar": False, "cerrar": False}
    drag = {"x": 0, "y": 0, "mov": False}

    def guardar():
        d = {"x": root.winfo_x(), "y": root.winfo_y(), "escala": escala, "oculta": oculta}
        guardar_conf(d)

    def ocultar():
        nonlocal oculta
        oculta = True
        cerrar_burbuja()
        root.withdraw()
        guardar()

    def mostrar():
        nonlocal oculta
        oculta = False
        root.deiconify()
        root.attributes("-topmost", True)
        sin_foco()
        guardar()

    def alternar():
        (mostrar if oculta else ocultar)()

    def set_escala(v):
        nonlocal escala
        escala = v
        pato.S = escala * dpi
        poner_tam()
        guardar()

    def a_la_esquina():
        nx, ny = esquina()
        root.geometry(f"+{nx}+{ny}")
        guardar()

    def cerrar():
        flags["cerrar"] = True

    def set_estado(e, texto=""):
        est["estado"], est["texto"], est["desde"] = e, texto, time.time()

    menu = tk.Menu(root, tearoff=0)
    menu.add_command(label="Ocultar  (Ctrl+Alt+P)", command=ocultar)
    sub = tk.Menu(menu, tearoff=0)
    for nombre, v in (("Pequeño", 0.7), ("Normal", 1.0), ("Grande", 1.4)):
        sub.add_command(label=nombre, command=lambda v=v: set_escala(v))
    menu.add_cascade(label="Tamaño", menu=sub)
    menu.add_command(label="Ver última respuesta", command=lambda: (mostrar_burbuja(burb["texto"]) if burb["texto"] else None))
    menu.add_command(label="Volver a la esquina", command=a_la_esquina)
    menu.add_separator()
    menu.add_command(label="Cerrar a Pato", command=cerrar)

    def on_press(e):
        drag["x"], drag["y"], drag["mov"] = e.x_root - root.winfo_x(), e.y_root - root.winfo_y(), False

    def on_move(e):
        drag["mov"] = True
        nx, ny = ajustar(e.x_root - drag["x"], e.y_root - drag["y"])
        root.geometry(f"+{nx}+{ny}")
        colocar_burbuja()

    def on_release(e):
        if drag["mov"]:
            guardar()

    def on_menu(e):
        try:
            menu.tk_popup(e.x_root, e.y_root)
        finally:
            menu.grab_release()

    def on_doble(e):
        set_estado("hecho", "¡Cuac!")

    for w in (canvas, root):
        w.bind("<ButtonPress-1>", on_press)
        w.bind("<B1-Motion>", on_move)
        w.bind("<ButtonRelease-1>", on_release)
        w.bind("<Button-3>", on_menu)
        w.bind("<Double-Button-1>", on_doble)

    try:
        import keyboard
        keyboard.add_hotkey(HOTKEY, lambda: flags.__setitem__("alternar", True))
    except Exception:
        pass

    demo_estados = [("reposo", ""), ("escuchando", ""), ("pensando", ""), ("trabajando", "Buscando en internet"),
                    ("hablando", ""), ("hecho", ""), ("error", "")]
    t0 = time.time()
    ult = {"vivo": time.time(), "top": time.time(), "cmd": 0.0}

    def tick():
        ahora = time.time()
        # órdenes (voz / menú)
        try:
            if CMD.exists():
                orden = CMD.read_text(encoding="utf-8").strip().lower()
                CMD.unlink()
                if orden == "ocultar" and not oculta:
                    ocultar()
                elif orden == "mostrar" and oculta:
                    mostrar()
                elif orden == "alternar":
                    alternar()
        except Exception:
            pass
        if flags["alternar"]:
            flags["alternar"] = False
            alternar()
        if flags["cerrar"]:
            root.destroy()
            return

        if demo:
            i = int((ahora - t0) / 3.2) % len(demo_estados)
            e, tx = demo_estados[i]
            if est["estado"] != e:
                set_estado(e, tx)
        else:
            try:
                mt = ESTADO.stat().st_mtime
                if mt != est["mtime"]:
                    est["mtime"] = mt
                    d = json.loads(ESTADO.read_text(encoding="utf-8"))
                    set_estado(d.get("estado", "reposo"), d.get("texto", ""))
            except Exception:
                pass
            try:
                mt = RESP.stat().st_mtime
                if mt != resp_mt["v"]:
                    resp_mt["v"] = mt
                    mostrar_burbuja(json.loads(RESP.read_text(encoding="utf-8")).get("texto", ""))
            except Exception:
                pass
            if est["estado"] in ("escuchando", "pensando") and burb["win"] is not None and ahora - est["desde"] < 0.3:
                cerrar_burbuja()                     # empieza una orden nueva
            if burb["win"] is not None and ahora > burb["hasta"]:
                cerrar_burbuja()
            dur = ahora - est["desde"]
            if est["estado"] == "hecho" and dur > 2.4:
                set_estado("reposo")
            elif est["estado"] == "error" and dur > 4.0:
                set_estado("reposo")
            elif est["estado"] != "reposo" and dur > 400:       # por si algo se quedó colgado
                set_estado("reposo")
            if ahora - ult["vivo"] > 2:
                ult["vivo"] = ahora
                if not jarvis_vivo():
                    root.destroy()
                    return
        if ahora - ult["top"] > 3 and not oculta:
            ult["top"] = ahora
            root.attributes("-topmost", True)
        pato.cola = burb["win"] is not None
        if not oculta:
            pato.frame(ahora - t0, est["estado"], est["texto"], ahora - est["desde"])
        root.after(66, tick)

    tick()
    root.mainloop()


if __name__ == "__main__":
    main(demo="--demo" in sys.argv)
