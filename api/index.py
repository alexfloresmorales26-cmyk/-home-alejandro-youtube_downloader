"""
=============================================================================
MODULO: api/index.py
DESCRIPCION: Punto de entrada serverless para Vercel.
=============================================================================
"""

__version__ = "1.0.0"

import os
import shutil
import sys

# Anadir la raiz del proyecto al path para importar los modulos compartidos.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, jsonify, render_template, request, send_file

import cookies as cookie_config
from core import process_download_request, process_info_request
from downloader import has_ffmpeg
from utils import cleanup_temp_dirs, validate_youtube_url

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, "templates"),
    static_folder=os.path.join(PROJECT_ROOT, "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

# Cabeceras de seguridad aplicadas a todas las respuestas del servidor.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' https://cdnjs.cloudflare.com "
        "https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com "
        "https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    ),
}


@app.after_request
def _apply_security_headers(response):
    for name, value in SECURITY_HEADERS.items():
        response.headers[name] = value
    return response


# Limpieza de restos propios de ejecuciones anteriores (solo prefijo ytdl-).
cleanup_temp_dirs(max_age_hours=2)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
def api_info():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = {}
    res = process_info_request(str(data.get("url", "")).strip())
    return jsonify(res), 200 if res.get("success") else 400


@app.route("/api/cookies-status", methods=["GET"])
def api_cookies_status():
    """Endpoint de diagnostico: verifica la configuracion de cookies."""
    payload = cookie_config.cookies_status()
    payload["ffmpeg_available"] = has_ffmpeg()
    payload["yt_dlp_installed"] = True
    return jsonify(payload)


@app.route("/api/cleanup", methods=["POST"])
def api_cleanup():
    """Endpoint para limpieza manual de archivos temporales."""
    return jsonify({"success": True, "cleanup": cleanup_temp_dirs(2)})


@app.route("/api/download", methods=["GET", "POST"])
def api_download():
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = request.form or {}
        url = str(data.get("url", "")).strip()
        download_type = str(data.get("type", "video") or "video")
        quality = str(data.get("quality", "best") or "best")
    else:
        url = request.args.get("url", "").strip()
        download_type = request.args.get("type", "video")
        quality = request.args.get("quality", "best")

    # El frontend usa HEAD como preflight: solo valida la URL, sin descargar.
    if request.method == "HEAD":
        es_valido, mensaje = validate_youtube_url(url)
        if not es_valido:
            return jsonify({"success": False, "error": mensaje}), 400
        return "", 200

    temp_dir = None
    try:
        filepath, temp_dir, filename = process_download_request(
            url, download_type, quality
        )
        response = send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype="application/octet-stream",
        )
        response.call_on_close(
            lambda directory=temp_dir: shutil.rmtree(directory, ignore_errors=True)
        )
        return response
    except ValueError as exc:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"success": False, "error": str(exc)}), 500
