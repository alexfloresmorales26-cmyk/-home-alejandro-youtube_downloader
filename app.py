# -*- coding: utf-8 -*-
"""
=============================================================================
MODULO: app.py
DESCRIPCION: Servidor Web para el Descargador de YouTube.
             Soporta ejecución con Flask (para despliegue en Render, Railway, etc.)
             y modo nativo de respaldo con librerías estándar de Python.
=============================================================================
"""

import os
import sys
import json
import glob
import tempfile
import urllib.parse
import yt_dlp
from downloader import YouTubeDownloader, format_duration, format_bytes, has_ffmpeg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Lógica común de procesamiento de API
# ---------------------------------------------------------------------------
def process_info_request(url: str) -> dict:
    """Extrae metadatos y resoluciones del video usando yt-dlp."""
    if not url:
        return {"success": False, "error": "Debes ingresar una URL válida de YouTube."}

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    is_playlist = 'entries' in info
    if is_playlist:
        return {
            "success": True,
            "is_playlist": True,
            "title": info.get("title", "Lista de Reproducción"),
            "uploader": info.get("uploader", "Varios"),
            "total_items": len(info.get("entries", [])),
            "thumbnail": info.get("thumbnails", [{}])[-1].get("url", ""),
        }

    formats = info.get('formats', [])
    heights = set()
    for f in formats:
        if f.get('vcodec') != 'none' and f.get('height'):
            heights.add(f['height'])

    sorted_heights = sorted(list(heights), reverse=True)
    resolutions = [f"{h}p" for h in sorted_heights]
    if not resolutions:
        resolutions = ["1080p", "720p", "480p", "360p"]

    return {
        "success": True,
        "is_playlist": False,
        "title": info.get("title", "Sin título"),
        "uploader": info.get("uploader", "Desconocido"),
        "duration": format_duration(info.get("duration")),
        "view_count": f"{info.get('view_count', 0):,}" if info.get("view_count") else "N/A",
        "thumbnail": info.get("thumbnail", ""),
        "resolutions": resolutions,
    }


def process_download_request(url: str, download_type: str = "video", quality: str = "best") -> str:
    """Descarga el video/audio/miniatura en una carpeta temporal y retorna la ruta del archivo."""
    temp_dir = tempfile.mkdtemp(dir=DOWNLOADS_DIR)
    outtmpl = os.path.join(temp_dir, '%(title)s.%(ext)s')
    ffmpeg_available = has_ffmpeg()

    if download_type == "thumbnail":
        ydl_opts = {
            'writethumbnail': True,
            'skip_download': True,
            'outtmpl': outtmpl,
            'quiet': True,
        }
    elif download_type == "audio":
        audio_format = quality if quality in ["mp3", "m4a", "wav", "flac"] else "mp3"
        if ffmpeg_available:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': outtmpl,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_format,
                    'preferredquality': '192',
                }],
                'quiet': True,
            }
        else:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': outtmpl,
                'quiet': True,
            }
    else:  # video
        if quality and quality != "best":
            height = quality.replace('p', '')
            format_str = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best" if ffmpeg_available else f"best[height<={height}]/best"
        else:
            format_str = "bestvideo+bestaudio/best" if ffmpeg_available else "best"

        ydl_opts = {
            'format': format_str,
            'outtmpl': outtmpl,
            'merge_output_format': 'mp4' if ffmpeg_available else None,
            'quiet': True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    files = glob.glob(os.path.join(temp_dir, "*"))
    if not files:
        raise Exception("No se pudo generar el archivo de descarga.")
    return files[0]


# ---------------------------------------------------------------------------
# Modo 1: Flask (si está instalado)
# ---------------------------------------------------------------------------
try:
    from flask import Flask, render_template, request, jsonify, send_file
    FLASK_AVAILABLE = True
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/info", methods=["POST"])
    def api_info():
        data = request.get_json(silent=True) or {}
        res = process_info_request(data.get("url", "").strip())
        status = 200 if res.get("success") else 400
        return jsonify(res), status

    @app.route("/api/download", methods=["GET", "POST"])
    def api_download():
        if request.method == "POST":
            data = request.get_json(silent=True) or request.form or {}
            url = data.get("url", "").strip()
            download_type = data.get("type", "video")
            quality = data.get("quality", "best")
        else:
            url = request.args.get("url", "").strip()
            download_type = request.args.get("type", "video")
            quality = request.args.get("quality", "best")

        try:
            filepath = process_download_request(url, download_type, quality)
            return send_file(filepath, as_attachment=True, download_name=os.path.basename(filepath))
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

except ImportError:
    FLASK_AVAILABLE = False
    app = None


# ---------------------------------------------------------------------------
# Modo 2: Servidor HTTP Nativo de Python (Sin dependencias externas)
# ---------------------------------------------------------------------------
if not FLASK_AVAILABLE:
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    class StandaloneWebHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            if path == "/" or path == "/index.html":
                index_path = os.path.join(TEMPLATES_DIR, "index.html")
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

            if path.startswith("/static/"):
                rel_path = path[len("/static/"):]
                file_path = os.path.join(STATIC_DIR, rel_path)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    content_type = "text/css" if file_path.endswith(".css") else "application/javascript"
                    with open(file_path, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    return

            if path == "/api/download":
                query = urllib.parse.parse_qs(parsed.query)
                url = query.get("url", [""])[0]
                download_type = query.get("type", ["video"])[0]
                quality = query.get("quality", ["best"])[0]

                try:
                    filepath = process_download_request(url, download_type, quality)
                    filename = os.path.basename(filepath)
                    with open(filepath, "rb") as f:
                        content = f.read()

                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                except Exception as e:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
                return

            self.send_error(404, "Página no encontrada")

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/info":
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                try:
                    data = json.loads(body.decode("utf-8"))
                    res = process_info_request(data.get("url", "").strip())
                    self.send_response(200 if res.get("success") else 400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps(res).encode("utf-8"))
                except Exception as e:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
                return


def run_server():
    port = int(os.environ.get("PORT", 5000))
    if FLASK_AVAILABLE:
        print(f"\n[Flask] Iniciando servidor web en: http://localhost:{port}")
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        print(f"\n[HTTP Server Nativo] Iniciando servidor web en: http://localhost:{port}")
        server = HTTPServer(("0.0.0.0", port), StandaloneWebHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")


if __name__ == "__main__":
    run_server()
