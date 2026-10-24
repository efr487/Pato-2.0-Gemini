# Pato 2.0 para Gemini

Jarvis ("Pato"): asistente personal sobre una bóveda de notas Markdown (Obsidian), adaptado a **Gemini CLI**. Esta carpeta es la propia bóveda: clónala y úsala.

## Contenido
- `GEMINI.md` — Instrucciones del asistente. Gemini CLI las lee solo al abrir la carpeta.
- `.gemini/commands/` — Comandos `/hoy`, `/capturar <idea>`, `/investigar <tema>` y `/cierre`.
- `HUMANO/` y `MAQUINA/` — Estructura de la bóveda (vacía, sin notas personales).
- `SISTEMA/plantillas/` — Plantilla del diario.
- `SISTEMA/voz/` — Modo voz para Windows: mantén la tecla º o di "Hey Pato".

## Puesta en marcha (texto)
1. Instala Node.js (nodejs.org) y Git.
2. `npm install -g @google/gemini-cli`
3. `git clone https://github.com/efr487/Pato-2.0-Gemini.git` y entra en la carpeta.
4. Ejecuta `gemini` e inicia sesión con tu cuenta de Google.

## Modo voz (Windows)
1. Instala Python 3.12 y ejecuta `SISTEMA\voz\instalar.bat` (descarga los modelos de voz la primera vez).
2. Ejecuta `gemini` una vez en la carpeta para iniciar sesión.
3. Ejecuta `SISTEMA\voz\iniciar_jarvis_voz.bat`. Mantén º y habla, o di "Hey Pato".

El script llama a `gemini -p ... -o stream-json --approval-mode yolo`: Gemini actúa sin pedir permiso por cada herramienta, así que solo úsalo en una carpeta de confianza. Elige solo el modelo: `flash-lite` para órdenes simples, `flash` normal y `pro` para informes (se cambia en `jarvis_voz.py`).

## Correo, calendario, Drive y Spotify
Las conexiones de la versión original eran de Claude y no vienen incluidas. Se pueden añadir con servidores MCP: `gemini mcp add <nombre> <comando>` (ver documentación de Gemini CLI).

## Aviso
Adaptado sin poder probarlo con Gemini CLI instalado (basado en su documentación). Si algo falla, mira `SISTEMA/voz/jarvis_voz.log`.
