# 🎬 Descargador de YouTube Profesional (Desktop GUI, Web & CLI)

Aplicación todo-en-uno en Python para descargar videos, audios en MP3/M4A/WAV, miniaturas y listas de reproducción de YouTube en alta definición.

---

## 🌟 3 Formas de Usarlo

### 1. 🖥️ Modo Aplicación de Escritorio (Desktop GUI - Recomendado)
Abre una ventana independiente nativa en tu pantalla (como Spotify o Discord):
```bash
python3 gui.py
```

---

### 2. 🌐 Modo Servidor / Página Web
Ejecuta el servidor web para acceder desde cualquier navegador o dispositivo en tu red:
```bash
python3 app.py
```
Abre en tu navegador: **`http://localhost:5000`**

---

### 3. 💻 Modo Consola / Terminal (CLI)
Si prefieres usarlo directamente desde la línea de comandos:
```bash
python3 main.py
```

---

## ✨ Características Principales

- 🔍 **Buscador con Previsualización**: Pega el enlace y mira la portada, autor, vistas y duración al instante.
- 🎥 **Calidades de Video**: 1080p, 720p, 480p, 360p en formato MP4.
- 🎵 **Formatos de Audio**: MP3 (192 kbps), M4A, WAV y FLAC.
- 🖼️ **Miniaturas HD**: Descarga directa de la portada original del video.
- 📋 **Listas de Reproducción**: Descarga playlists completas organizadas en subcarpetas.
- 🎨 **Diseño Moderno y Responsivo**: Interfaz fluida con Tailwind CSS y tema oscuro futurista púrpura.
- 🍪 **Soporte de Cookies**: Para evitar bloqueos de YouTube ("Sign in to confirm you're not a bot"), configura la variable de entorno `YTDLP_COOKIES` con el contenido de tu archivo `cookies.txt`.

---

## 🍪 Configuración de Cookies (Importante para despliegue en la nube)

YouTube puede bloquear descargas desde servidores sin navegador. Para evitar el error **"Sign in to confirm you're not a bot"**, necesitas proporcionar cookies de tu sesión de YouTube.

### Cómo obtener tus cookies:

1. Instala la extensión **"Get cookies.txt LOCALLY"** en tu navegador (Chrome, Firefox, Edge).
2. Ve a [youtube.com](https://youtube.com) e inicia sesión.
3. Haz clic en la extensión y exporta las cookies como archivo `cookies.txt`.
4. Copia todo el contenido del archivo `cookies.txt`.

### En Render (despliegue en la nube):

Ve a tu servicio en Render → **Environment Variables** y añade:

| Clave | Valor |
|-------|-------|
| `YTDLP_COOKIES` | (pega aquí todo el contenido de tu `cookies.txt`) |

O alternativamente, sube el archivo `cookies.txt` y usa:
| Clave | Valor |
|-------|-------|
| `YTDLP_COOKIES_FILE` | `/ruta/al/archivo/cookies.txt` |

### En ejecución local:

Crea un archivo `.env` en la raíz del proyecto:
```
YTDLP_COOKIES_FILE=./cookies.txt
```
O exporta la variable:
```bash
export YTDLP_COOKIES="$(cat cookies.txt)"
```

---

## 📁 Estructura del Proyecto

```text
youtube_downloader/
├── gui.py                # 🖥️ Lanzador de la Aplicación de Escritorio
├── app.py                # 🌐 Servidor Web (Flask / HTTP nativo)
├── main.py               # 💻 Menú interactivo por consola
├── downloader.py         # ⚙️ Motor de descargas con yt-dlp
├── api/index.py          # ☁️ Punto de entrada serverless para Vercel
├── templates/
│   └── index.html        # 🎨 Interfaz gráfica visual (diseño futurista púrpura)
├── static/
│   ├── css/styles.css    # 🖌️ Estilos visuales
│   └── js/app.js         # ⚡ Lógica interactiva en JavaScript
├── test_downloader.py    # 🧪 Pruebas unitarias
├── requirements.txt      # 📦 Dependencias (flask, yt-dlp, gunicorn, pywebview)
├── requirements-dev.txt  # 🛠️ Dependencias de desarrollo
├── Dockerfile            # 🐳 Docker para despliegue
├── render.yaml           # ☁️ Configuración para Render
├── vercel.json           # ☁️ Configuración para Vercel
├── Procfile              # 📦 Procfile para Render/Heroku
├── runtime.txt           # 🐍 Versión de Python
└── downloads/            # 📂 Carpeta donde se guardan las descargas
```

---

## ☁️ Despliegue en la Nube

### Render (Recomendado - incluye ffmpeg)

Render despliega usando el `Dockerfile` que incluye **ffmpeg**, permitiendo descargas completas de video y conversiones de audio.

1. Conecta tu repositorio de GitHub a Render.
2. Crea un nuevo **Web Service**.
3. Añade la variable de entorno `YTDLP_COOKIES` con tus cookies de YouTube.
4. Render construirá la imagen y desplegará automáticamente.

### Vercel

1. Conecta tu repositorio a Vercel.
2. Añade la variable de entorno `YTDLP_COOKIES`.
3. Despliega.

**Nota:** En Vercel no hay ffmpeg disponible, por lo que las conversiones de audio y merge de video+audio tendrán limitaciones.

---

## 🧰 Instalación y ejecución local (recomendado)

1. Crear y activar un entorno virtual:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Instalar dependencias de producción:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. (Opcional) Configurar cookies para evitar bloqueos de YouTube:
   ```bash
   export YTDLP_COOKIES="$(cat cookies.txt)"
   ```

4. Ejecutar tests unitarios:
   ```bash
   python -m unittest -v
   ```

5. Ejecutar la aplicación en modo consola (CLI):
   ```bash
   python main.py
   ```

6. Ejecutar la aplicación como servidor Flask (modo web):
   ```bash
   python app.py
   ```
   Abre en tu navegador: `http://localhost:5000`

---

## 🐳 Docker (recomendado para despliegue)

Construir la imagen Docker:
```bash
docker build -t youtube-downloader:latest .
```

Ejecutar en modo consola (interactivo):
```bash
docker run --rm -it youtube-downloader:latest
```

Ejecutar en modo Flask (servidor web, puerto 8080):
```bash
docker run --rm -p 8080:8080 -e APP_MODE=flask -e YTDLP_COOKIES="$(cat cookies.txt)" youtube-downloader:latest
```

---

## 🔧 Notas y requisitos del sistema

- **ffmpeg** debe estar disponible para habilitar conversiones de audio/video. El Dockerfile ya lo instala.
- **Cookies de YouTube**: Para descargas desde servidores en la nube, configura `YTDLP_COOKIES` con tu archivo `cookies.txt` para evitar bloqueos de bot.
- Para que los commits automatizados realizados por los workflows cuenten como tus contributions, asegúrate de que el email del autor de los commits esté asociado a tu cuenta de GitHub.

## 🩺 Solución rápida de problemas

| Error | Solución |
|-------|----------|
| "Sign in to confirm you're not a bot" | Configura `YTDLP_COOKIES` con tus cookies de YouTube |
| Descarga falla al combinar video y audio | Instala `ffmpeg` en tu sistema |
| Puerto 5000 ocupado | Inicia con otro puerto: `PORT=8080 python3 app.py` |
| Cookies expiradas | Renueva las cookies en tu navegador y actualiza la variable de entorno |
