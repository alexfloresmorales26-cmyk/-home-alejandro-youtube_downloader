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
- 🎨 **Diseño Moderno y Responsivo**: Interfaz fluida con Tailwind CSS y tema oscuro.

---

## 📁 Estructura del Proyecto

```text
youtube_downloader/
├── gui.py                # 🖥️ Lanzador de la Aplicación de Escritorio
├── app.py                # 🌐 Servidor Web (Flask / HTTP nativo)
├── main.py               # 💻 Menú interactivo por consola
├── downloader.py         # ⚙️ Motor de descargas con yt-dlp
├── templates/
│   └── index.html        # 🎨 Interfaz gráfica visual
├── static/
│   ├── css/styles.css    # 🖌️ Estilos visuales
│   └── js/app.js         # ⚡ Lógica interactiva en JavaScript
├── test_downloader.py    # 🧪 Pruebas unitarias
├── requirements.txt      # 📦 Dependencias (flask, yt-dlp, gunicorn, pywebview)
└── downloads/            # 📂 Carpeta donde se guardan las descargas
```

---

## ☁️ Despliegue Gratis en la Nube (Render / Railway)

1. Sube tu proyecto a GitHub.
2. En [render.com](https://render.com), crea un nuevo **Web Service**.
3. Conecta tu repositorio y usa:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. ¡Listo! Obtendrás un enlace público para compartir.
