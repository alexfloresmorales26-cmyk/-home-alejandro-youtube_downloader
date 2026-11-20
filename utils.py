# -*- coding: utf-8 -*-
"""
=============================================================================
MODULO: utils.py
DESCRIPCION: Utilidades compartidas de validacion de URLs, limpieza de
             temporales y seleccion de archivos descargados.
=============================================================================
"""

import os
import shutil
import tempfile
import time
from urllib.parse import parse_qs, urlparse

# Prefijo propio para no borrar directorios temporales de otras aplicaciones.
TEMP_DIR_PREFIX = "ytdl-"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_ROOT = os.environ.get("YTDLP_TEMP_DIR", "").strip()
if TEMP_ROOT and not os.path.isabs(TEMP_ROOT):
    TEMP_ROOT = os.path.join(BASE_DIR, TEMP_ROOT)


def get_temp_root() -> str:
    """Devuelve la raiz de temporales configurada o la del sistema."""
    root = TEMP_ROOT or tempfile.gettempdir()
    os.makedirs(root, exist_ok=True)
    return root


ALLOWED_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

DOWNLOAD_TEMP_SUFFIXES = (".part", ".ytdl", ".temp", ".tmp")
ACTIVE_DOWNLOAD_SUFFIXES = (".part", ".ytdl")

YOUTUBE_URL_ERROR = (
    "La URL no parece ser de YouTube. Ejemplos validos:\n"
    "  - https://www.youtube.com/watch?v=VIDEO_ID\n"
    "  - https://youtu.be/VIDEO_ID\n"
    "  - https://www.youtube.com/shorts/VIDEO_ID\n"
    "  - https://www.youtube.com/playlist?list=PLAYLIST_ID"
)


def validate_youtube_url(url: str) -> tuple[bool, str]:
    """Valida que la URL sea de YouTube y tenga un formato soportado.

    Retorna (es_valido, mensaje_error).
    """
    if not url or not url.strip():
        return False, "Debes ingresar una URL de YouTube."

    candidate = url.strip()
    if "://" not in candidate:
        candidate = "https://" + candidate

    try:
        parsed = urlparse(candidate)
    except ValueError:
        return False, YOUTUBE_URL_ERROR

    if parsed.scheme not in ("http", "https"):
        return False, YOUTUBE_URL_ERROR

    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_YOUTUBE_HOSTS:
        return False, YOUTUBE_URL_ERROR

    path = parsed.path.rstrip("/")

    if host in ("youtu.be", "www.youtu.be"):
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) == 1:
            return True, ""
        return False, YOUTUBE_URL_ERROR

    if path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0].strip()
        if video_id:
            return True, ""
        return False, YOUTUBE_URL_ERROR

    if path.startswith(("/shorts/", "/live/", "/embed/")):
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 2 and parts[1]:
            return True, ""
        return False, YOUTUBE_URL_ERROR

    if path == "/playlist":
        playlist_id = parse_qs(parsed.query).get("list", [""])[0].strip()
        if playlist_id:
            return True, ""
        return False, YOUTUBE_URL_ERROR

    return False, YOUTUBE_URL_ERROR


def _has_active_download(directory: str, cutoff: float) -> bool:
    """Detecta descargas en curso para no borrarlas durante la limpieza.

    Un video puede tardar horas: el directorio conserva su mtime original,
    pero el archivo ``.part`` se sigue modificando. Si hay restos parciales o
    archivos recientes, se considera activo y no se elimina.
    """
    try:
        for root, _dirs, files in os.walk(directory):
            for filename in files:
                if filename.lower().endswith(ACTIVE_DOWNLOAD_SUFFIXES):
                    return True
                try:
                    if os.path.getmtime(os.path.join(root, filename)) > cutoff:
                        return True
                except OSError:
                    continue
    except OSError:
        return True
    return False


def cleanup_temp_dirs(max_age_hours: int = 2) -> dict:
    """Elimina directorios temporales propios (prefijo ytdl-) ya finalizados."""
    cleaned = 0
    errors = 0
    freed_mb = 0.0

    try:
        tmp_dir = get_temp_root()
        for entry in os.listdir(tmp_dir):
            if not entry.startswith(TEMP_DIR_PREFIX):
                continue

            entry_path = os.path.join(tmp_dir, entry)
            if not os.path.isdir(entry_path):
                continue

            try:
                mtime = os.path.getmtime(entry_path)
                age_hours = (time.time() - mtime) / 3600.0
                if age_hours <= max_age_hours:
                    continue

                cutoff = time.time() - (max_age_hours * 3600)
                if _has_active_download(entry_path, cutoff):
                    continue

                size = 0
                for root, _dirs, files in os.walk(entry_path):
                    for filename in files:
                        try:
                            size += os.path.getsize(os.path.join(root, filename))
                        except OSError:
                            pass

                shutil.rmtree(entry_path, ignore_errors=True)
                if os.path.exists(entry_path):
                    errors += 1
                else:
                    cleaned += 1
                    freed_mb += size / (1024 * 1024)
            except OSError:
                errors += 1
    except OSError:
        pass

    return {
        "cleaned_dirs": cleaned,
        "errors": errors,
        "freed_mb": round(freed_mb, 2),
    }


def list_downloaded_files(temp_dir: str) -> list[str]:
    """Lista los archivos finales de una descarga, ignorando restos parciales."""
    files: list[str] = []
    try:
        entries = os.listdir(temp_dir)
    except OSError:
        return files

    for name in entries:
        path = os.path.join(temp_dir, name)
        if not os.path.isfile(path):
            continue
        if name.lower().endswith(DOWNLOAD_TEMP_SUFFIXES):
            continue
        try:
            if os.path.getsize(path) <= 0:
                continue
        except OSError:
            continue
        files.append(path)

    return files


def pick_downloaded_file(temp_dir: str) -> str | None:
    """Devuelve el archivo de mayor tamano de la carpeta temporal."""
    files = list_downloaded_files(temp_dir)
    if not files:
        return None
    return max(files, key=lambda path: os.path.getsize(path))
