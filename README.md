# 🎬 Descargador de YouTube Profesional (Web & CLI)

Aplicación web moderna y herramienta de línea de comandos en Python para descargar videos, audios en MP3/M4A/WAV, miniaturas y listas de reproducción de YouTube en alta definición.

---

## 🌟 Dos Formas de Usarlo

### 1. 🌐 Modo Página Web (Para ti y para compartir con otros)
Ejecuta el servidor web con un solo comando:
```bash
python3 app.py
```
Abre tu navegador en: **`http://localhost:5000`*

#### ✨ Características de la Web:
- 🔍 **Buscador con Previsualización**: Pega el enlace y mira la portada, autor, vistas y duración al instante.
- 🎚️ **Selector de Calidad**: 1080p, 720p, 480p, 360p (MP4).
- 🎵 **Extracción de Audio**: MP3 (192 kbps), M4A, WAV, FLAC.
- 🖼️ **Descarga de Portadas**: Obtén la miniatura original en máxima resolución.
- 📱 **Diseño Responsivo**: Funciona en computadoras, tablets y teléfonos móviles.

---

### 2. 💻 Modo Consola / Terminal (CLI)
Si prefieres usarlo directamente desde la terminal:
```bash
python3 main.py
```

---

## 📁 Estructura del Proyecto

```text
youtube_downloader/
├── app.py                # Servidor Web (Flask / HTTP nativo)
├── main.py               # Menú interactivo por consola
├── downloader.py         # Motor de descarga con yt-dlp
├── templates/
│   └── index.html        # Página web con diseño moderno y Tailwind CSS
├── static/
│   ├── css/styles.css    # Estilos visuales
│   └── js/app.js         # Lógica interactiva del frontend
├── requirements.txt      # Dependencias (flask, yt-dlp, gunicorn)
└── downloads/            # Carpeta donde se guardan las descargas
```

---

## ☁️ ¿Cómo publicarlo en internet para que cualquiera pueda usarlo?

Puedes subirlo **gratis** a la nube en menos de 2 minutos usando **Render** o **Railway**:

### Despliegue en Render (Gratis):
1. Sube tu proyecto a GitHub.
2. Entra a [render.com](https://render.com) y crea una cuenta gratuita.
3. Haz clic en **New +** ➔ **Web Service**.
4. Conecta tu repositorio de GitHub.
5. Configura:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
6. Haz clic en **Create Web Service**. ¡Listo! Render te dará un enlace público (ej: `https://tu-app.onrender.com`) para compartir con quien quieras.
