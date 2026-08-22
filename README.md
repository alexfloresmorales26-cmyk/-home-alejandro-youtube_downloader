# 🎬 Descargador Avanzado de YouTube en Python

Herramienta completa, modular y 100% en código abierto Python para descargar videos, pistas de audio en múltiples formatos, miniaturas, subtítulos y listas de reproducción completas de YouTube utilizando [`yt-dlp`](https://github.com/yt-dlp/yt-dlp).

---

## ✨ Funcionalidades Principales

- 🎥 **Descarga de Videos**: Máxima resolución (4K, 1080p, 720p, 480p) en formato MP4.
- 🎵 **Extracción de Audio**: Formatos MP3, M4A, WAV y FLAC.
- 📋 **Listas de Reproducción (Playlists)**: Descarga carpetas completas y ordenadas por número de pista.
- 🖼️ **Miniaturas (Thumbnails)**: Descarga de la portada del video en máxima resolución.
- 💬 **Subtítulos**: Descarga de subtítulos en español e inglés (.vtt / .srt).
- 📊 **Progreso en Tiempo Real**: Barra visual con porcentaje, tamaño descargado, velocidad y tiempo estimado (ETA).
- 🎨 **Interfaz de Consola Estilizada**: Menú interactivo a color y soporte de comandos CLI.
- 🔄 **Detección Automática de FFmpeg**: Modo compatible sin fallos si FFmpeg no está instalado.

---

## 📁 Estructura del Proyecto

```text
youtube_downloader/
├── .gitignore          # Ignora entornos virtuales y carpeta de descargas
├── README.md           # Guía completa de uso e instalación
├── requirements.txt    # Librerías necesarias (yt-dlp)
├── downloader.py       # Motor de descargas con soporte para video, audio, subs y playlists
├── main.py             # Menú interactivo estilizado y CLI
├── test_downloader.py  # Suite de pruebas unitarias
└── downloads/          # Directorio donde se guardan los archivos descargados
```

---

## 🚀 Instalación y Uso Rápido

1. **Abrir la terminal en la carpeta:**
   ```bash
   cd /home/alejandro/.gemini/antigravity/scratch/youtube_downloader
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar el menú interactivo:**
   ```bash
   python3 main.py
   ```

---

## 💻 Opciones de Línea de Comandos (CLI)

También puedes usar el script directamente desde la terminal o integrarlo en otros programas:

- **Descargar video en máxima calidad:**
  ```bash
  python3 main.py "https://www.youtube.com/watch?v=VIDEO_ID"
  ```

- **Descargar video en resolución específica (ej. 1080p):**
  ```bash
  python3 main.py -r 1080p "https://www.youtube.com/watch?v=VIDEO_ID"
  ```

- **Descargar audio en formato MP3:**
  ```bash
  python3 main.py -a --format mp3 "https://www.youtube.com/watch?v=VIDEO_ID"
  ```

- **Descargar una lista de reproducción completa en video:**
  ```bash
  python3 main.py -p "https://www.youtube.com/playlist?list=PLAYLIST_ID"
  ```

- **Descargar solo la miniatura (Thumbnail):**
  ```bash
  python3 main.py -t "https://www.youtube.com/watch?v=VIDEO_ID"
  ```

- **Descargar subtítulos:**
  ```bash
  python3 main.py -s "https://www.youtube.com/watch?v=VIDEO_ID"
  ```

- **Definir carpeta de guardado personalizada:**
  ```bash
  python3 main.py -o ~/MisVideos "https://www.youtube.com/watch?v=VIDEO_ID"
  ```

---

## 🧪 Ejecutar Pruebas Unitarias

Para comprobar el correcto funcionamiento de las funciones y formateadores:
```bash
python3 -m unittest test_downloader.py
```
