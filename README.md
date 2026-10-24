# Pato 2.0 para Antigravity CLI

Jarvis ("Pato"): asistente personal sobre una bóveda de notas Markdown (Obsidian), adaptado a **Antigravity CLI** (`agy`), que sustituye a Gemini CLI. Esta carpeta es la propia bóveda: clónala y úsala.

## Contenido
- `AGENTS.md` — Instrucciones del asistente. Antigravity las lee solo al abrir la carpeta.
- `.agents/skills/` — Comandos `/hoy`, `/capturar <idea>`, `/investigar <tema>` y `/cierre`.
- `HUMANO/` y `MAQUINA/` — Estructura de la bóveda (vacía, sin notas personales).
- `SISTEMA/plantillas/` — Plantilla del diario.
- `SISTEMA/voz/` — Modo voz para Windows: mantén la tecla º o di "Hey Pato".

## Puesta en marcha (texto)
1. Instala Git.
2. En PowerShell: `irm https://antigravity.google/cli/install.ps1 | iex`
3. `git clone https://github.com/efr487/Pato-2.0-Gemini.git` y entra en la carpeta.
4. Ejecuta `agy` e inicia sesión con tu cuenta de Google.

## Modo voz (Windows)
1. Instala Python 3.12 y ejecuta `SISTEMA\voz\instalar.bat` (descarga los modelos de voz la primera vez).
2. Ejecuta `agy` una vez en la carpeta para iniciar sesión.
3. Ejecuta `SISTEMA\voz\iniciar_jarvis_voz.bat`. Mantén º y habla, o di "Hey Pato".

El script llama a `agy -p ... --dangerously-skip-permissions`: actúa sin pedir permiso por cada herramienta, así que solo úsalo en una carpeta de confianza. Continúa la conversación con `--continue`. El modelo es el que tengas por defecto en agy; para enrutar por orden, activa `ENRUTAR_MODELO` en `jarvis_voz.py` y rellena `MODELO_*` con los nombres de `agy models`.

## Correo, calendario, Drive y Spotify
No vienen incluidos. Se añaden como servidores MCP: `agy mcp add <nombre> <comando>` (las opciones van antes del nombre).

## Aviso
Adaptado sin tener `agy` instalado, según guías de terceros: los nombres de flags y carpetas pueden variar. Si algo falla, mira `SISTEMA/voz/jarvis_voz.log`.
