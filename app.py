"""
=============================================================================
MODULO: app.py
DESCRIPCION: Servidor Web para el Descargador de YouTube.
             Soporta ejecucion con Flask (Render, Railway, etc.) y modo
             nativo de respaldo con librerias estandar de Python.
=============================================================================
"""

__version__ = "1.0.0"

import json
import mimetypes
import os
import shutil
import urllib.parse

import cookies as cookie_config
from core import process_download_request, process_info_request
from downloader import has_ffmpeg
from utils import cleanup_temp_dirs, validate_youtube_url

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Limpieza de restos propios de ejecuciones anteriores (solo prefijo ytdl-).
cleanup_temp_dirs(max_age_hours=2)


# ---------------------------------------------------------------------------
# Modo 1: Flask (si esta instalado)
# ---------------------------------------------------------------------------
try:
    from flask import Flask, jsonify, render_template, request, send_file

    FLASK_AVAILABLE = True
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/info", methods=["POST"])
    def api_info():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}
        res = process_info_request(str(data.get("url", "")).strip())
        status = 200 if res.get("success") else 400
        return jsonify(res), status

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

except ImportError:
    FLASK_AVAILABLE = False
    app = None


# ---------------------------------------------------------------------------
# Modo 2: Servidor HTTP nativo de Python (sin dependencias externas)
# ---------------------------------------------------------------------------
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def _content_disposition(filename: str) -> str:
    """Genera una cabecera Content-Disposition segura para nombres UTF-8."""
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "descarga"
    ascii_name = ascii_name.replace('"', "").replace("\r", "").replace("\n", "")
    encoded = urllib.parse.quote(filename, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"


class StandaloneWebHandler(SimpleHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_request_data(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            length = 0
        body = self.rfile.read(length) if length else b""
        if not body:
            return {}

        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                data = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                return {}
            return data if isinstance(data, dict) else {}

        try:
            parsed = urllib.parse.parse_qs(body.decode("utf-8"))
        except UnicodeDecodeError:
            return {}
        return {key: values[0] for key, values in parsed.items() if values}

    def _handle_download(
        self, url: str, download_type: str = "video", quality: str = "best"
    ) -> None:
        try:
            filepath, temp_dir, filename = process_download_request(
                url, download_type, quality
            )
        except ValueError as exc:
            self._send_json(400, {"success": False, "error": str(exc)})
            return
        except Exception as exc:
            self._send_json(500, {"success": False, "error": str(exc)})
            return

        try:
            size = os.path.getsize(filepath)
        except OSError as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            self._send_json(500, {"success": False, "error": str(exc)})
            return

        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Disposition", _content_disposition(filename))
            self.end_headers()
            with open(filepath, "rb") as file_obj:
                shutil.copyfileobj(file_obj, self.wfile, length=1024 * 1024)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            index_path = os.path.join(TEMPLATES_DIR, "index.html")
            try:
                with open(index_path, "rb") as file_obj:
                    content = file_obj.read()
            except OSError as exc:
                self._send_json(500, {"success": False, "error": str(exc)})
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/cookies-status":
            payload = cookie_config.cookies_status()
            payload["ffmpeg_available"] = has_ffmpeg()
            payload["yt_dlp_installed"] = True
            self._send_json(200, payload)
            return

        if path.startswith("/static/"):
            rel_path = path[len("/static/") :]
            file_path = os.path.realpath(os.path.join(STATIC_DIR, rel_path))
            static_root = os.path.realpath(STATIC_DIR)
            try:
                inside_static = (
                    os.path.commonpath([static_root, file_path]) == static_root
                )
            except ValueError:
                inside_static = False

            if inside_static and os.path.isfile(file_path):
                content_type = (
                    mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                )
                with open(file_path, "rb") as file_obj:
                    content = file_obj.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        if path == "/api/download":
            query = urllib.parse.parse_qs(parsed.query)
            self._handle_download(
                query.get("url", [""])[0],
                query.get("type", ["video"])[0],
                query.get("quality", ["best"])[0],
            )
            return

        self.send_error(404, "Pagina no encontrada")

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/download":
            query = urllib.parse.parse_qs(parsed.query)
            es_valido, _mensaje = validate_youtube_url(query.get("url", [""])[0])
            self.send_response(200 if es_valido else 400)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if parsed.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_error(405, "Metodo no permitido")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/info":
            data = self._read_request_data()
            res = process_info_request(str(data.get("url", "")).strip())
            self._send_json(200 if res.get("success") else 400, res)
            return

        if parsed.path == "/api/download":
            data = self._read_request_data()
            self._handle_download(
                str(data.get("url", "")).strip(),
                data.get("type", "video"),
                data.get("quality", "best"),
            )
            return

        if parsed.path == "/api/cleanup":
            self._send_json(200, {"success": True, "cleanup": cleanup_temp_dirs(2)})
            return

        self.send_error(404, "Pagina no encontrada")


def run_server():
    try:
        port = int(os.environ.get("PORT", 5000))
    except (TypeError, ValueError):
        port = 5000
    if FLASK_AVAILABLE:
        print(f"\n[Flask] Iniciando servidor web en: http://localhost:{port}")
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        print(
            f"\n[HTTP Server Nativo] Iniciando servidor web en: "
            f"http://localhost:{port}"
        )
        server = ThreadingHTTPServer(("0.0.0.0", port), StandaloneWebHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")


if __name__ == "__main__":
    run_server()
