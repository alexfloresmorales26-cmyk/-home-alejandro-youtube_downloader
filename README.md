# 🎬 Descargador de YouTube (Desktop GUI, Web & CLI)

Aplicación todo-en-uno en Python para descargar videos, audios (MP3/M4A/WAV/FLAC), miniaturas y listas de reproducción de YouTube. Funciona con [yt-dlp](https://github.com/yt-dlp/yt-dlp) y ofrece tres modos de uso: aplicación de escritorio, servidor web y consola.

---

## 🌟 3 Formas de Usarlo

### 1. 🖥️ Modo Aplicación de Escritorio (Desktop GUI)

Arranca un servidor HTTP local y abre la interfaz en una ventana del navegador (modo aplicación si el navegador lo soporta):

```bash
python3 gui.py
```

La terminal debe permanecer abierta mientras usas la aplicación. Presiona `Ctrl + C` para cerrar.

---

### 2. 🌐 Modo Servidor / Página Web

Ejecuta el servidor web para acceder desde cualquier navegador:

```bash
python3 app.py
```

Abre en tu navegador: **`http://localhost:5000`**

Puedes cambiar el puerto con la variable de entorno `PORT`:

```bash
PORT=8080 python3 app.py
```

---

### 3. 💻 Modo Consola / Terminal (CLI)

Menú interactivo por consola:

```bash
python3 main.py
```

Uso directo con argumentos (ejemplo: descargar audio en MP3):

```bash
python3 main.py "https://www.youtube.com/watch?v=VIDEO_ID" --audio --format mp3
```

---

## ✨ Características Principales

- 🔍 **Buscador con previsualización**: pega el enlace y consulta portada, autor, vistas y duración al instante.
- 🎥 **Calidades de video**: 1080p, 720p, 480p, 360p (y las disponibles según el video) en formato MP4.
- 🎵 **Formatos de audio**: MP3 (192 kbps), M4A, WAV y FLAC (requiere ffmpeg para conversión).
- 🖼️ **Miniaturas HD**: descarga directa de la portada original del video.
- 📋 **Listas de reproducción**: descarga playlists completas organizadas en subcarpetas.
- 💬 **Subtítulos**: descarga subtítulos (.vtt / .srt) en español o inglés.
- 🖥️ **Tres interfaces**: GUI de escritorio, servidor web (Flask / HTTP nativo) y CLI interactivo.
- 🌑 **Tema oscuro** y diseño responsivo con Tailwind CSS.

---

## 📁 Estructura del Proyecto

```text
youtube_downloader/
├── gui.py                  # 🖥️ Lanzador de la aplicación de escritorio
├── app.py                  # 🌐 Servidor web (Flask con fallback HTTP nativo)
├── main.py                 # 💻 Menú interactivo por consola y CLI
├── downloader.py           # ⚙️ Motor de descargas con yt-dlp
├── index.py                # 🌐 Flask app para despliegue en Vercel / otros
├── api/index.py            # 🌐 Endpoint serverless para Vercel
├── templates/
│   └── index.html          # 🎨 Interfaz visual del modo web
├── static/
│   ├── css/
│   │   ├── styles.css      # 🖌️ Estilos personalizados
│   │   └── tailwind.min.css # ⚡ Tailwind CSS (compilado)
│   └── js/
│       └── app.js          # ⚡ Lógica interactiva en JavaScript
├── test_downloader.py      # 🧪 Pruebas unitarias
├── requirements.txt        # 📦 Dependencias de producción
├── requirements-dev.txt    # 🛠️ Dependencias de desarrollo
├── Dockerfile              # 🐳 Imagen Docker
├── render.yaml             # ☁️ Despliegue en Render
├── vercel.json             # ☁️ Despliegue en Vercel
├── Procfile                # ☁️ Despliegue en Heroku / Railway
├── runtime.txt             # ☁️ Versión de Python para PaaS
├── .flake8                 # 🔎 Configuración de flake8
├── .pre-commit-config.yaml # 🪝 Ganchos pre-commit
├── .github/
│   ├── workflows/          # ⚙️ CI / autoformateo
│   ├── pull_request_template.md
│   └── ISSUE_TEMPLATE/
├── downloads/              # 📂 Carpeta donde se guardan las descargas (ignorada en git)
└── README.md               # 📖 Esta documentación
```

---

## 🧰 Instalación y ejecución local (recomendado)

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/alexfloresmorales26-cmyk/-home-alejandro-youtube_downloader.git
   cd youtube_downloader
   ```

2. Crear y activar un entorno virtual:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instalar dependencias de producción:

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Instalar dependencias de desarrollo (opcional):

   ```bash
   pip install -r requirements-dev.txt
   ```

5. Ejecutar pruebas unitarias:

   ```bash
   python -m unittest -v
   ```

6. Ejecutar en modo consola (CLI):

   ```bash
   python main.py
   ```

7. Ejecutar como servidor Flask (modo web):

   ```bash
   python app.py
   # O con gunicorn en producción:
   gunicorn -b 0.0.0.0:8080 app:app
   ```

8. Ejecutar en modo escritorio (GUI):

   ```bash
   python gui.py
   ```

---

## 🖥️ Uso del CLI (`main.py`)

```
usage: main.py [-h] [-a] [--format {mp3,m4a,wav,flac}] [-r RESOLUTION]
               [-p] [-t] [-s] [-o OUTPUT] [url]

Argumentos:
  url                    URL del video o lista de reproducción de YouTube
  -a, --audio            Descargar únicamente el audio
  --format               Formato de audio (mp3, m4a, wav, flac) [default: mp3]
  -r, --resolution       Resolución de video (ej. 1080p, 720p, 480p)
  -p, --playlist         Indica que la URL es una lista de reproducción
  -t, --thumbnail        Descargar solo la miniatura
  -s, --subtitles        Descargar subtítulos
  -o, --output           Carpeta de destino [default: downloads]
```

Ejemplos:

```bash
# Descargar video en máxima calidad
python main.py "https://youtu.be/VIDEO_ID"

# Descargar solo audio en MP3
python main.py "https://youtu.be/VIDEO_ID" --audio

# Descargar video en 720p
python main.py "https://youtu.be/VIDEO_ID" -r 720p

# Descargar playlist completa como audio
python main.py "https://youtube.com/playlist?list=LIST_ID" -p --audio
```

---

## 🌐 API del Modo Web

Cuando ejecutas `app.py` (o `index.py`), expone dos endpoints JSON:

### `POST /api/info`

Obtiene metadatos de un video o playlist.

**Body:**
```json
{ "url": "https://www.youtube.com/watch?v=VIDEO_ID" }
```

**Respuesta (video):**
```json
{
  "success": true,
  "is_playlist": false,
  "title": "Título del video",
  "uploader": "Canal",
  "duration": "10:25",
  "view_count": "1.234.567",
  "thumbnail": "https://...",
  "resolutions": ["1080p", "720p", "480p", "360p"]
}
```

**Respuesta (playlist):**
```json
{
  "success": true,
  "is_playlist": true,
  "title": "Nombre de la playlist",
  "uploader": "Canal",
  "total_items": 25,
  "thumbnail": "https://..."
}
```

### `GET/POST /api/download`

Descarga el archivo y lo devuelve como adjunto.

**Parámetros (query o JSON body):**
- `url`: URL de YouTube (requerida)
- `type`: `video` | `audio` | `thumbnail` [default: `video`]
- `quality`: resolución (ej. `1080p`) o formato de audio (`mp3`, `m4a`, `wav`, `flac`) [default: `best`]

**Ejemplo con curl:**
```bash
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://youtu.be/VIDEO_ID","type":"audio","quality":"mp3"}' \
  --output audio.mp3
```

---

## ⚙️ Variables de Entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `PORT` | Puerto del servidor web | `5000` |
| `APP_MODE` | Si es `flask`, usa gunicorn sobre `app:app` | — |
| `FLASK_APP` | Aplicación Flask | `app.py` |
| `FLASK_ENV` | Entorno de Flask | `production` |

---

## 🐳 Docker (recomendado para despliegue)

Construir la imagen:

```bash
docker build -t youtube-downloader:latest .
```

Ejecutar en modo consola (CLI interactivo):

```bash
docker run --rm -it youtube-downloader:latest
```

Ejecutar en modo servidor web (puerto 8080):

```bash
docker run --rm -p 8080:8080 -e APP_MODE=flask youtube-downloader:latest
```

> **Nota:** ffmpeg ya está instalado en la imagen Docker, por lo que las conversiones de audio y el merge de video+audio funcionan sin configuración extra.

---

## ☁️ Despliegue en la Nube

### Render

1. Sube tu proyecto a GitHub.
2. En [render.com](https://render.com), crea un nuevo **Web Service**.
3. Conecta tu repositorio y usa:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -b 0.0.0.0:10000 app:app`
   - Variable de entorno: `APP_MODE=flask`

También puedes usar el archivo `render.yaml` incluido en el repositorio.

### Railway / Heroku

Usa el `Procfile`:

```text
web: gunicorn -b 0.0.0.0:$PORT app:app
```

y `runtime.txt`:

```text
python-3.10
```

### Vercel

El proyecto incluye `api/index.py` y `vercel.json` para desplegar como función serverless en Vercel.

---

## 🔧 Requisitos del Sistema

- **Python 3.10+**
- **ffmpeg**: necesario para convertir audio (MP3, M4A, WAV, FLAC) y para combinar video + audio en la máxima calidad. Si no está instalado, la aplicación sigue funcionando con descargas nativas de yt-dlp, pero sin conversiones de formato.
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: descarga desde [ffmpeg.org](https://ffmpeg.org/download.html)

---

## 🩺 Solución Rápida de Problemas

| Problema | Solución |
|----------|----------|
| Descarga falla al combinar video y audio | Instala `ffmpeg` y vuelve a intentarlo. |
| Puerto 5000 ocupado | Usa otro puerto: `PORT=8080 python3 app.py`. |
| Error de conversión de audio | Verifica que ffmpeg esté instalado y en el PATH. |
| La GUI no abre el navegador | Abre manualmente `http://127.0.0.1:5000` en tu navegador. |
| Descarga de playlist muy larga | Las playlists se descargan en su propia subcarpeta dentro de `downloads/`. |

---

## 📄 Licencia

Proyecto de código abierto. Diseñado para uso personal y educativo.

---

*Última actualización: noviembre 2026*