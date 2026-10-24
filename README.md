# Pato 2.0 para Gemini

Versión de Jarvis (asistente personal sobre una bóveda de Obsidian) preparada para usarse con **Gemini CLI** en lugar de Claude.

## Contenido
- `GEMINI.md` — Instrucciones del asistente. Gemini CLI lee este archivo automáticamente al abrir la carpeta.
- `comandos/` — Comandos `hoy`, `capturar`, `investigar` y `cierre`, en Markdown. Gemini CLI usa archivos TOML en `.gemini/commands/`; hay que convertirlos si quieres los atajos.
- `plantillas/` — Plantillas de notas.
- `voz/` — Scripts de modo voz de Windows. **Están escritos para Claude** (usan el CLI de Claude); se incluyen como referencia y necesitan adaptarse para llamar a Gemini.

## Puesta en marcha
1. Instala Node.js desde nodejs.org.
2. En una terminal: `npm install -g @google/gemini-cli`
3. Crea tu bóveda con las carpetas `HUMANO/` y `MAQUINA/` (ver `GEMINI.md`).
4. Copia este repositorio dentro de la bóveda o úsalo como base.
5. Entra en la carpeta y ejecuta `gemini`. Inicia sesión con tu cuenta de Google.

## Limitaciones
- Las conexiones de correo, calendario, Drive y Spotify son de Claude y no se trasladan automáticamente.
- No incluye notas personales, memoria ni registros: solo la configuración.
