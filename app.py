"""
=============================================================================
MODULO: app.py
DESCRIPCION: Servidor Web para el Descargador de YouTube.
             Soporta ejecución con Flask (para despliegue en Render, Railway, etc.)
             y modo nativo de respaldo con librerías estándar de Python.
=============================================================================
"""

import os
import json
import glob
import tempfile
import urllib.parse
import re
import yt_dlp
from downloader import format_duration, has_ffmpeg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Lectura de cookies para YouTube (evita bloqueo de bot "Sign in to confirm")
# ---------------------------------------------------------------------------
COOKIES_FILE = os.environ.get("YTDLP_COOKIES_FILE", "")
COOKIES_CONTENT = os.environ.get("YTDLP_COOKIES", "")
COOKIES_PATH: str | None = None
COOKIES_VALID = False
COOKIES_ERROR = ""


def _is_netscape_cookies(content: str) -> bool:
    """Verifica si el contenido tiene formato Netscape cookies.txt."""
    if not content or not content.strip():
        return False
    lines = content.strip().splitlines()
    valid_lines = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Aceptar tanto tabuladores como múltiples espacios como separadores
        fields = [f for f in re.split(r"[\t ]{2,}", stripped) if f]
        if len(fields) >= 7:
            valid_lines += 1
    return valid_lines > 0


def _fix_netscape_cookies(content: str) -> str:
    """Intenta reparar automáticamente el formato Netscape cookies.txt.
    
    - Convierte múltiples espacios a tabuladores
    - Elimina texto no-cookie después de la última línea válida
    - Filtra líneas que no tengan al menos 7 campos
    """
    if not content or not content.strip():
        return content

    lines = content.strip().splitlines()
    fixed_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            fixed_lines.append(stripped)
            continue
        # Convertir 2+ espacios a tabulador
        normalized = re.sub(r"[\t ]{2,}", "\t", stripped)
        fields = normalized.split("\t")
        if len(fields) >= 7:
            fixed_lines.append(normalized)
        # Si una línea no tiene 7 campos, asumir que es texto extra y detenerse
        elif fixed_lines:
            break

    return "\n".join(fixed_lines)


if COOKIES_CONTENT:
    if not _is_netscape_cookies(COOKIES_CONTENT):
        # Intentar reparar automáticamente
        fixed = _fix_netscape_cookies(COOKIES_CONTENT)
        if fixed != COOKIES_CONTENT and _is_netscape_cookies(fixed):
            COOKIES_CONTENT = fixed
            _cf = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
            _cf.write(COOKIES_CONTENT)
            _cf.close()
            COOKIES_PATH = str(_cf.name)
            COOKIES_VALID = True
            COOKIES_ERROR = "Cookies reparadas automáticamente (formato ajustado)."
        else:
            COOKIES_ERROR = (
                "El contenido de YTDLP_COOKIES no tiene formato Netscape válido. "
                "Posibles causas: espacios en lugar de tabuladores, o texto extra "
                "después de las cookies. Exporta nuevamente con 'Get cookies.txt LOCALLY'."
            )
    else:
        _cf = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        _cf.write(COOKIES_CONTENT)
        _cf.close()
        COOKIES_PATH = str(_cf.name)
        COOKIES_VALID = True
elif COOKIES_FILE and os.path.exists(COOKIES_FILE):
    try:
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            file_content = f.read()
        if not _is_netscape_cookies(file_content):
            fixed = _fix_netscape_cookies(file_content)
            if fixed != file_content and _is_netscape_cookies(fixed):
                # Escribir el archivo reparado
                with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                    f.write(fixed)
                COOKIES_PATH = str(COOKIES_FILE)
                COOKIES_VALID = True
                COOKIES_ERROR = "Cookies del archivo reparadas automáticamente."
            else:
                COOKIES_ERROR = (
                    f"El archivo {COOKIES_FILE} no tiene formato Netscape cookies.txt válido."
                )
        else:
            COOKIES_PATH = str(COOKIES_FILE)
            COOKIES_VALID = True
    except Exception as e:
        COOKIES_ERROR = f"No se pudo leer {COOKIES_FILE}: {e}"


def _ydl_opts_with_cookies(extra: dict) -> dict:
    """Agrega cookies a las opciones de yt-dlp si están disponibles."""
    if COOKIES_PATH:
        extra["cookiefile"] = COOKIES_PATH
    return extra


# ---------------------------------------------------------------------------
# Lógica común de procesamiento de API y render
# ---------------------------------------------------------------------------
def process_info_request(url: str) -> dict:
    """Extrae metadatos y resoluciones del video usando yt-dlp."""
    if not url:
        return {"success": False, "error": "Debes ingresar una URL válida de YouTube."}

    ydl_opts = _ydl_opts_with_cookies({
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "remote_components": ["ejs:github"],
    })
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return {"success": False, "error": str(e)}

    is_playlist = "entries" in info
    if is_playlist:
        return {
            "success": True,
            "is_playlist": True,
            "title": info.get("title", "Lista de Reproducción"),
            "uploader": info.get("uploader", "Varios"),
            "total_items": len(info.get("entries", [])),
            "thumbnail": info.get("thumbnails", [{}])[-1].get("url", ""),
        }

    formats = info.get("formats", [])
    heights = set()
    for f in formats:
        if f.get("vcodec") != "none" and f.get("height"):
            heights.add(f["height"])

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
        "view_count": f"{info.get('view_count', 0):,}"
        if info.get("view_count")
        else "N/A",
        "thumbnail": info.get("thumbnail", ""),
        "resolutions": resolutions,
    }


def process_download_request(
    url: str, download_type: str = "video", quality: str = "best"
) -> str:
    """Descarga el archivo en una carpeta temporal y retorna su ruta."""
    temp_dir = tempfile.mkdtemp()
    outtmpl = os.path.join(temp_dir, "%(title)s.%(ext)s")
    ffmpeg_available = has_ffmpeg()

    if download_type == "thumbnail":
        ydl_opts = _ydl_opts_with_cookies({
            "writethumbnail": True,
            "skip_download": True,
            "outtmpl": outtmpl,
            "quiet": True,
            "remote_components": ["ejs:github"],
        })
    elif download_type == "audio":
        audio_format = quality if quality in ["mp3", "m4a", "wav", "flac"] else "mp3"
        if ffmpeg_available:
            ydl_opts = _ydl_opts_with_cookies({
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": audio_format,
                        "preferredquality": "192",
                    }
                ],
                "quiet": True,
                "remote_components": ["ejs:github"],
            })
        else:
            ydl_opts = _ydl_opts_with_cookies({
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "quiet": True,
                "remote_components": ["ejs:github"],
            })
    else:  # video
        if quality and quality != "best":
            height = quality.replace("p", "")
            if ffmpeg_available:
                format_str = (
                    f"bestvideo[height={height}][ext=mp4]+bestaudio[ext=m4a]"
                    f"/bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]"
                    f"/bestvideo[height<={height}]+bestaudio"
                    f"/best[height<={height}]"
                    f"/bestvideo+bestaudio"
                    f"/best"
                )
            else:
                format_str = (
                    f"best[height={height}][ext=mp4]"
                    f"/best[height<={height}][ext=mp4]"
                    f"/best[height<={height}]"
                    f"/best"
                )
        else:
            if ffmpeg_available:
                format_str = (
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
                )
            else:
                format_str = "best[ext=mp4]/best"

        ydl_opts = _ydl_opts_with_cookies({
            "format": format_str,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4" if ffmpeg_available else None,
            "quiet": True,
            "remote_components": ["ejs:github"],
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    files = glob.glob(os.path.join(temp_dir, "*"))
    if not files:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception("No se pudo generar el archivo de descarga.")

    filepath = files[0]
    # Leer el contenido antes de borrar la carpeta temporal
    with open(filepath, "rb") as f:
        content = f.read()
    filename = os.path.basename(filepath)

    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)
    return content, filename


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

    @app.route("/api/cookies-status", methods=["GET"])
    def api_cookies_status():
        """Endpoint de diagnóstico: verifica si las cookies de YouTube están configuradas."""
        import os as _os

        cookiefile_exists = False
        cookiefile_readable = False
        cookiefile_size = 0
        if COOKIES_PATH and _os.path.exists(COOKIES_PATH):
            cookiefile_exists = True
            try:
                cookiefile_size = _os.path.getsize(COOKIES_PATH)
                with open(COOKIES_PATH, "r") as _f:
                    _f.read(1)
                cookiefile_readable = True
            except Exception:
                cookiefile_readable = False

        return jsonify({
            "cookies_configured": COOKIES_PATH is not None,
            "cookies_valid": COOKIES_VALID,
            "cookies_source": "YTDLP_COOKIES" if COOKIES_CONTENT else (
                "YTDLP_COOKIES_FILE" if COOKIES_FILE else "none"
            ),
            "cookies_path": COOKIES_PATH,
            "cookiefile_exists": cookiefile_exists,
            "cookiefile_readable": cookiefile_readable,
            "cookiefile_size": cookiefile_size,
            "cookies_error": COOKIES_ERROR,
            "ffmpeg_available": has_ffmpeg(),
            "yt_dlp_installed": True,
        })

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
            content, filename = process_download_request(url, download_type, quality)
            return send_file(
                content,
                as_attachment=True,
                download_name=filename,
                mimetype="application/octet-stream",
            )
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

except ImportError:
    FLASK_AVAILABLE = False
    app = None


# ---------------------------------------------------------------------------
# Modo 2: Servidor HTTP Nativo de Python (Sin dependencias externas)
# ---------------------------------------------------------------------------
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
            rel_path = path[len("/static/") :]
            file_path = os.path.abspath(os.path.join(STATIC_DIR, rel_path))
            static_root = os.path.abspath(STATIC_DIR)
            if os.path.commonpath(
                [static_root, file_path]
            ) == static_root and os.path.isfile(file_path):
                content_type = (
                    "text/css"
                    if file_path.endswith(".css")
                    else "application/javascript"
                )
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
                content, filename = process_download_request(url, download_type, quality)

                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header(
                    "Content-Disposition", f'attachment; filename="{filename}"'
                )
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"success": False, "error": str(e)}).encode("utf-8")
                )
            return

        self.send_error(404, "Página no encontrada")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/info":
            content_length = int(self.headers.get("Content-Length", 0))
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
                self.wfile.write(
                    json.dumps({"success": False, "error": str(e)}).encode("utf-8")
                )
            return


def run_server():
    port = int(os.environ.get("PORT", 5000))
    if FLASK_AVAILABLE:
        print(f"\n[Flask] Iniciando servidor web en: http://localhost:{port}")
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        print(
            f"\n[HTTP Server Nativo] Iniciando servidor web en: http://localhost:{port}"
        )
        server = HTTPServer(("0.0.0.0", port), StandaloneWebHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")


if __name__ == "__main__":
    run_server()
