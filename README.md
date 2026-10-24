# Pato 2.0 para Antigravity CLI

Pato (Jarvis) es un asistente personal que trabaja sobre una carpeta de notas en Markdown (una "bóveda" de Obsidian). Le escribes o le hablas, y lee, crea y ordena tus notas. Funciona con **Antigravity CLI** (comando `agy`), el programa de Google que sustituye a Gemini CLI.

Esta carpeta ya es la bóveda: la descargas y la usas tal cual.

## Qué necesitas antes de empezar
- Un PC con Windows 10 u 11.
- Una cuenta de Google (la misma con la que usas Gemini).
- Conexión a internet.
- Opcional: [Obsidian](https://obsidian.md) para ver y editar las notas con comodidad. No es obligatorio.

## Qué hay en la carpeta
- `AGENTS.md`: las instrucciones de Pato (quién es, cómo trabaja, qué carpetas puede tocar). `agy` las lee solo al abrir la carpeta; no hay que hacer nada.
- `.agents/skills/`: los comandos `/hoy`, `/capturar <idea>`, `/investigar <tema>` y `/cierre`.
- `HUMANO/`: tus notas. Pato las lee, pero no las cambia sin permiso.
- `MAQUINA/`: el espacio de Pato (memoria, diario, tareas, investigaciones).
- `SISTEMA/plantillas/`: plantillas, por ejemplo la del diario.
- `SISTEMA/voz/`: el modo voz para Windows.

## Parte 1: instalación y uso por texto

### Paso 1. Instalar Git
1. Entra en https://git-scm.com/download/win y descarga el instalador.
2. Ábrelo y pulsa "Next" en todo hasta terminar.

### Paso 2. Abrir PowerShell
Pulsa la tecla Windows, escribe `PowerShell` y pulsa Enter. Se abre una ventana azul o negra donde se escriben los comandos. Copia cada comando de abajo, pégalo con clic derecho y pulsa Enter.

### Paso 3. Instalar Antigravity CLI
```
irm https://antigravity.google/cli/install.ps1 | iex
```
Cuando termine, **cierra PowerShell y ábrelo de nuevo**. Comprueba que funciona con:
```
agy --version
```
Si dice que no reconoce `agy`, reinicia el PC y vuelve a probar.

### Paso 4. Descargar la bóveda
```
cd $HOME\Documents
git clone https://github.com/efr487/Pato-2.0-Gemini.git
cd Pato-2.0-Gemini
```
El repositorio es privado: la primera vez Git te pedirá iniciar sesión en GitHub en el navegador, y necesitas haber sido invitado con tu cuenta.

### Paso 5. Iniciar sesión y probar
```
agy
```
La primera vez se abre el navegador para que inicies sesión con tu cuenta de Google. Acepta los permisos y vuelve a la ventana. Después escribe, por ejemplo:
```
/hoy
```
o simplemente "hola, ¿qué puedes hacer?". Para salir, cierra la ventana o pulsa Ctrl+C dos veces.

## Parte 2: modo voz (opcional)

Con el modo voz mantienes pulsada la tecla **º** y hablas, o dices **"Hey Pato"**. Pato te responde en voz alta.

### Paso 1. Instalar Python 3.12
Descárgalo de https://www.python.org/downloads/ . En el instalador **marca la casilla "Add python.exe to PATH"** antes de pulsar Install.

### Paso 2. Instalar las piezas del modo voz
En la carpeta de la bóveda, abre `SISTEMA\voz` y haz doble clic en `instalar.bat`. La primera vez descarga los modelos de voz (puede tardar varios minutos; no cierres la ventana).

### Paso 3. Asegurarte de haber iniciado sesión
Si no has hecho el Paso 5 de la Parte 1, hazlo ahora: la voz usa la misma sesión de `agy`.

### Paso 4. Arrancar
Haz doble clic en `SISTEMA\voz\iniciar_jarvis_voz.bat` y deja la ventana abierta (puedes minimizarla). Mantén **º**, habla, y suelta.

Si el micrófono no responde, mira en Configuración de Windows > Privacidad > Micrófono que las aplicaciones de escritorio tengan acceso.

### Aviso de seguridad
Para no interrumpirte, el modo voz lanza `agy` con `--dangerously-skip-permissions`: Pato puede leer, crear y modificar archivos y abrir programas sin pedir permiso cada vez. Úsalo solo en esta carpeta y no la pongas en un sitio con archivos importantes.

### Ajustes opcionales
Se cambian abriendo `SISTEMA\voz\jarvis_voz.py` con el Bloc de notas:
- Modelo: por defecto usa el de `agy`. Para elegir otro, escribe `agy models` para ver los nombres, pon `ENRUTAR_MODELO = True` y rellena `MODELO_SIMPLE`, `MODELO_NORMAL` y `MODELO_POTENTE`.
- Tiempo máximo por orden: `TIMEOUT_AGY` (300 segundos).

## Correo, calendario, Drive y Spotify
No vienen incluidos. Se añaden como servidores MCP con `agy mcp add <nombre> <comando>` (las opciones, como `--header`, van antes del nombre). Cada servicio tiene sus propias instrucciones; búscalas por su nombre y "MCP server".

## Si algo falla
- `agy` no se reconoce: cierra y abre PowerShell, o reinicia el PC.
- La voz no contesta: abre `SISTEMA\voz\jarvis_voz.log` y mira las últimas líneas; suele indicar el motivo.
- Pide permiso en cada acción en modo texto: es normal; en modo texto Pato pregunta antes de actuar.
- Este proyecto se adaptó sin poder probarlo con `agy` instalado, basándose en guías de terceros. Si algún comando o carpeta no coincide con tu versión, revisa `agy --help`.
