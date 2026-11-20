# -*- coding: utf-8 -*-
"""
=============================================================================
MODULO: core.py
DESCRIPCION: Logica compartida de extraccion de metadatos y descargas.
             La usan tanto el servidor Flask (app.py) como el entrypoint
             serverless de Vercel (api/index.py).
=============================================================================
"""

import copy
import os
import re
import shutil
import tempfile
import threading
import time
import zipfile
from collections import OrderedDict

import yt_dlp

from cookies import ydl_opts_with_cookies
from downloader import _build_video_format, format_duration, has_ffmpeg
from utils import (
    TEMP_DIR_PREFIX,
    get_temp_root,
    list_downloaded_files,
    validate_youtube_url,
)

DOWNLOAD_TYPES = {"video", "audio", "thumbnail"}
AUDIO_FORMATS = {"mp3", "m4a", "wav", "flac"}
VIDEO_QUALITY_RE = re.compile(r"^(\d{3,4})p$")


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    """Lee un entero de entorno sin romper la app si es invalido."""
    try:
        value = int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, value)


# Cache TTL de metadatos: evita repetir extracciones de ~4-5 segundos.
INFO_CACHE_TTL = _env_int("YTDLP_INFO_CACHE_TTL", 120, 0)
INFO_CACHE_MAX = _env_int("YTDLP_INFO_CACHE_MAX", 64, 0)
MAX_CONCURRENT_DOWNLOADS = _env_int("YTDLP_MAX_CONCURRENT_DOWNLOADS", 2, 1)

_INFO_CACHE: "OrderedDict[str, tuple[float, dict]]" = OrderedDict()
_INFO_CACHE_LOCK = threading.Lock()
_DOWNLOAD_SEMAPHORE = threading.BoundedSemaphore(MAX_CONCURRENT_DOWNLOADS)


def clear_info_cache() -> None:
    """Vacia la cache de metadatos (pruebas y limpieza manual)."""
    with _INFO_CACHE_LOCK:
        _INFO_CACHE.clear()


def _cache_get(url: str) -> dict | None:
    if INFO_CACHE_TTL <= 0 or INFO_CACHE_MAX <= 0:
        return None
    now = time.monotonic()
    with _INFO_CACHE_LOCK:
        cached = _INFO_CACHE.get(url)
        if cached is None:
            return None
        stored_at, payload = cached
        if now - stored_at >= INFO_CACHE_TTL:
            _INFO_CACHE.pop(url, None)
            return None
        _INFO_CACHE.move_to_end(url)
        return copy.deepcopy(payload)


def _cache_put(url: str, payload: dict) -> None:
    if INFO_CACHE_TTL <= 0 or INFO_CACHE_MAX <= 0:
        return
    with _INFO_CACHE_LOCK:
        _INFO_CACHE[url] = (time.monotonic(), copy.deepcopy(payload))
        _INFO_CACHE.move_to_end(url)
        while len(_INFO_CACHE) > INFO_CACHE_MAX:
            _INFO_CACHE.popitem(last=False)


def _normalize_download_options(download_type, quality) -> tuple[str, str]:
    """Normaliza los parametros que llegan desde la API o la CLI."""
    normalized_type = str(download_type or "video").strip().lower()
    if normalized_type not in DOWNLOAD_TYPES:
        normalized_type = "video"

    normalized_quality = str(quality or "best").strip().lower()
    if normalized_type == "audio" and normalized_quality not in AUDIO_FORMATS:
        normalized_quality = "mp3"
    elif (
        normalized_type == "video"
        and normalized_quality != "best"
        and not VIDEO_QUALITY_RE.fullmatch(normalized_quality)
    ):
        normalized_quality = "best"
    return normalized_type, normalized_quality


def _video_height(quality: str) -> str | None:
    """Devuelve la altura solo si la calidad tiene el formato NNNp valido."""
    match = VIDEO_QUALITY_RE.fullmatch(quality)
    if not match or int(match.group(1)) <= 0:
        return None
    return match.group(1)


def process_info_request(url: str) -> dict:
    """Extrae metadatos y resoluciones usando una cache TTL en memoria."""
    es_valido, mensaje = validate_youtube_url(url)
    if not es_valido:
        return {"success": False, "error": mensaje}

    cache_key = url.strip()
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    result = _extract_info(cache_key)
    if result.get("success"):
        _cache_put(cache_key, result)
    return result


def _extract_info(url: str) -> dict:
    """Consulta yt-dlp y normaliza la respuesta de metadatos."""
    ydl_opts = ydl_opts_with_cookies(
        {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "noplaylist": True,
            "socket_timeout": 30,
            "remote_components": ["ejs:github"],
        }
    )
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    if not info:
        return {
            "success": False,
            "error": "No se pudo obtener informacion del contenido.",
        }

    if info.get("entries") is not None:
        entries = info.get("entries")
        total_items = info.get("playlist_count")
        if total_items is None:
            try:
                total_items = len(entries) if entries is not None else 0
            except TypeError:
                total_items = 0
        thumbnails = info.get("thumbnails") or []
        thumbnail = info.get("thumbnail") or (
            thumbnails[-1].get("url", "") if thumbnails else ""
        )
        return {
            "success": True,
            "is_playlist": True,
            "title": info.get("title") or "Lista de Reproduccion",
            "uploader": info.get("uploader") or "Varios",
            "total_items": total_items,
            "thumbnail": thumbnail,
        }

    formats = info.get("formats") or []
    heights = {
        fmt["height"]
        for fmt in formats
        if fmt.get("vcodec") != "none" and fmt.get("height")
    }
    resolutions = [f"{height}p" for height in sorted(heights, reverse=True)]
    if not resolutions:
        resolutions = ["1080p", "720p", "480p", "360p"]

    view_count = info.get("view_count")
    return {
        "success": True,
        "is_playlist": False,
        "title": info.get("title") or "Sin titulo",
        "uploader": info.get("uploader") or "Desconocido",
        "duration": format_duration(info.get("duration")),
        "view_count": f"{view_count:,}" if view_count else "N/A",
        "thumbnail": info.get("thumbnail") or "",
        "resolutions": resolutions,
    }


def process_download_request(
    url: str, download_type: str = "video", quality: str = "best"
) -> tuple[str, str, str]:
    """Descarga el contenido en una carpeta temporal.

    Retorna (ruta_archivo, directorio_temporal, nombre_archivo). El llamador es
    responsable de borrar el directorio temporal cuando termine de enviar el
    archivo. Si la descarga falla, esta funcion limpia el directorio y relanza
    la excepcion.
    """
    es_valido, mensaje = validate_youtube_url(url)
    if not es_valido:
        raise ValueError(mensaje)

    download_type, quality = _normalize_download_options(download_type, quality)
    with _DOWNLOAD_SEMAPHORE:
        return _download_to_temp(url, download_type, quality)


def _download_to_temp(
    url: str, download_type: str, quality: str
) -> tuple[str, str, str]:
    """Descarga real; el semaforo se adquiere en process_download_request."""
    temp_dir = tempfile.mkdtemp(prefix=TEMP_DIR_PREFIX, dir=get_temp_root())
    outtmpl = os.path.join(temp_dir, "%(title)s.%(ext)s")
    ffmpeg_available = has_ffmpeg()

    try:
        if download_type == "thumbnail":
            ydl_opts = ydl_opts_with_cookies(
                {
                    "writethumbnail": True,
                    "skip_download": True,
                    "outtmpl": outtmpl,
                    "quiet": True,
                    "no_warnings": True,
                    "noplaylist": True,
                    "socket_timeout": 30,
                    "remote_components": ["ejs:github"],
                }
            )
        elif download_type == "audio":
            audio_format = quality
            options = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "socket_timeout": 30,
                "remote_components": ["ejs:github"],
            }
            if ffmpeg_available:
                options["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": audio_format,
                        "preferredquality": "192",
                    }
                ]
            ydl_opts = ydl_opts_with_cookies(options)
        else:
            height = _video_height(quality)
            format_str = _build_video_format(height=height, ffmpeg=ffmpeg_available)
            ydl_opts = ydl_opts_with_cookies(
                {
                    "format": format_str,
                    "outtmpl": outtmpl,
                    "merge_output_format": "mp4" if ffmpeg_available else None,
                    "quiet": True,
                    "no_warnings": True,
                    "noplaylist": True,
                    "socket_timeout": 30,
                    "remote_components": ["ejs:github"],
                }
            )

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = list_downloaded_files(temp_dir)
        if not files:
            raise RuntimeError("No se pudo generar el archivo de descarga.")

        if len(files) == 1:
            filepath = files[0]
            return filepath, temp_dir, os.path.basename(filepath)

        # Varios archivos (playlist, miniaturas multiples): se entrega un ZIP.
        zip_path = os.path.join(temp_dir, "descarga.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zip_file:
            for file_path in files:
                zip_file.write(file_path, arcname=os.path.basename(file_path))
        return zip_path, temp_dir, "descarga.zip"
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
