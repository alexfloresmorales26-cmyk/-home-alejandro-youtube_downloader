import sys
import os

# Añadir la raíz del proyecto al path para importar módulos
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, render_template, request, jsonify, send_file
import tempfile
import glob
import urllib.parse
import shutil
import os as os_module
import yt_dlp
from downloader import YouTubeDownloader, format_duration, format_bytes, has_ffmpeg

app = Flask(__name__,
    template_folder=os_module.path.join(PROJECT_ROOT, "templates"),
    static_folder=os_module.path.join(PROJECT_ROOT, "static"))

BASE_DIR = PROJECT_ROOT
TEMPLATES_DIR = os_module.path.join(BASE_DIR, "templates")
STATIC_DIR = os_module.path.join(BASE_DIR, "static")

# ---------------------------------------------------------------------------
# Lectura de cookies para YouTube (evita bloqueo de bot "Sign in to confirm")
# ---------------------------------------------------------------------------
COOKIES_FILE = os_module.environ.get("YTDLP_COOKIES_FILE", "")
COOKIES_CONTENT = os_module.environ.get("YTDLP_COOKIES", "")
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
        fields = stripped.split("\t")
        if len(fields) >= 7:
            valid_lines += 1
    return valid_lines > 0


if COOKIES_CONTENT:
    if not _is_netscape_cookies(COOKIES_CONTENT):
        COOKIES_ERROR = (
            "El contenido de YTDLP_COOKIES no parece ser un archivo cookies.txt "
            "en formato Netscape. Asegúrate de exportarlo con la extensión "
            "'Get cookies.txt LOCALLY' desde youtube.com."
        )
    else:
        _cf = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        _cf.write(COOKIES_CONTENT)
        _cf.close()
        COOKIES_PATH = str(_cf.name)
        COOKIES_VALID = True
elif COOKIES_FILE and os_module.path.exists(COOKIES_FILE):
    try:
        with open(COOKIES_FILE, "r", encoding="utf-8") as f:
            file_content = f.read()
        if not _is_netscape_cookies(file_content):
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
# Rutas de la API
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def api_info():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"success": False, "error": "Debes ingresar una URL válida de YouTube."}), 400

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
        return jsonify({"success": False, "error": str(e)}), 400

    is_playlist = "entries" in info
    if is_playlist:
        return jsonify({
            "success": True,
            "is_playlist": True,
            "title": info.get("title", "Lista de Reproducción"),
            "uploader": info.get("uploader", "Varios"),
            "total_items": len(info.get("entries", [])),
            "thumbnail": info.get("thumbnails", [{}])[-1].get("url", ""),
        })

    formats = info.get("formats", [])
    heights = set()
    for f in formats:
        if f.get("vcodec") != "none" and f.get("height"):
            heights.add(f["height"])

    sorted_heights = sorted(list(heights), reverse=True)
    resolutions = [f"{h}p" for h in sorted_heights] if sorted_heights else ["1080p", "720p", "480p", "360p"]

    return jsonify({
        "success": True,
        "is_playlist": False,
        "title": info.get("title", "Sin título"),
        "uploader": info.get("uploader", "Desconocido"),
        "duration": format_duration(info.get("duration")),
        "view_count": f"{info.get('view_count', 0):,}" if info.get("view_count") else "N/A",
        "thumbnail": info.get("thumbnail", ""),
        "resolutions": resolutions,
    })


@app.route("/api/cookies-status", methods=["GET"])
def api_cookies_status():
    """Endpoint de diagnóstico: verifica si las cookies de YouTube están configuradas."""
    return jsonify({
        "cookies_configured": COOKIES_PATH is not None,
        "cookies_valid": COOKIES_VALID,
        "cookies_source": "YTDLP_COOKIES" if COOKIES_CONTENT else (
            "YTDLP_COOKIES_FILE" if COOKIES_FILE else "none"
        ),
        "cookies_path": COOKIES_PATH,
        "cookies_error": COOKIES_ERROR,
        "ffmpeg_available": has_ffmpeg(),
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

    if not url:
        return jsonify({"success": False, "error": "URL requerida"}), 400

    temp_dir = tempfile.mkdtemp()
    outtmpl = os_module.path.join(temp_dir, "%(title)s.%(ext)s")
    ffmpeg_available = has_ffmpeg()

    try:
        if download_type == "thumbnail":
            ydl_opts = _ydl_opts_with_cookies({
                "writethumbnail": True,
                "skip_download": True,
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
                "remote_components": ["ejs:github"],
            })
        elif download_type == "audio":
            audio_format = quality if quality in ["mp3", "m4a", "wav", "flac"] else "mp3"
            if ffmpeg_available:
                ydl_opts = _ydl_opts_with_cookies({
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": audio_format,
                        "preferredquality": "192",
                    }],
                    "quiet": True,
                    "no_warnings": True,
                    "remote_components": ["ejs:github"],
                })
            else:
                ydl_opts = _ydl_opts_with_cookies({
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "quiet": True,
                    "no_warnings": True,
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
                    format_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
                else:
                    format_str = "best[ext=mp4]/best"

            ydl_opts = _ydl_opts_with_cookies({
                "format": format_str,
                "outtmpl": outtmpl,
                "merge_output_format": "mp4" if ffmpeg_available else None,
                "quiet": True,
                "no_warnings": True,
                "remote_components": ["ejs:github"],
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = glob.glob(os_module.path.join(temp_dir, "*"))
        if not files:
            return jsonify({"success": False, "error": "No se pudo generar el archivo de descarga."}), 500

        filepath = files[0]
        filename = os_module.path.basename(filepath)

        with open(filepath, "rb") as f:
            content = f.read()

        shutil.rmtree(temp_dir, ignore_errors=True)

        return send_file(
            content,
            as_attachment=True,
            download_name=filename,
            mimetype="application/octet-stream",
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
