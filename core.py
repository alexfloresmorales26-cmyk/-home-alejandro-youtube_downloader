# -*- coding: utf-8 -*-
"""
=============================================================================
MODULO: core.py
DESCRIPCION: Logica compartida de extraccion de metadatos y descargas.
             La usan tanto el servidor Flask (app.py) como el entrypoint
             serverless de Vercel (api/index.py).
=============================================================================
"""

import os
import shutil
import tempfile
import zipfile

import yt_dlp

from cookies import ydl_opts_with_cookies
from downloader import _build_video_format, format_duration, has_ffmpeg
from utils import TEMP_DIR_PREFIX, list_downloaded_files, validate_youtube_url


def process_info_request(url: str) -> dict:
    """Extrae metadatos y resoluciones del video usando yt-dlp."""
    es_valido, mensaje = validate_youtube_url(url)
    if not es_valido:
        return {"success": False, "error": mensaje}

    ydl_opts = ydl_opts_with_cookies(
        {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
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
                total_items = len(list(entries or []))
            except TypeError:
                total_items = 0
        thumbnails = info.get("thumbnails") or []
        thumbnail = (
            thumbnails[-1].get("url", "") if thumbnails else info.get("thumbnail", "")
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

    temp_dir = tempfile.mkdtemp(prefix=TEMP_DIR_PREFIX)
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
                    "remote_components": ["ejs:github"],
                }
            )
        elif download_type == "audio":
            audio_format = (
                quality if quality in ("mp3", "m4a", "wav", "flac") else "mp3"
            )
            options = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
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
            height = quality.replace("p", "") if quality and quality != "best" else None
            format_str = _build_video_format(height=height, ffmpeg=ffmpeg_available)
            ydl_opts = ydl_opts_with_cookies(
                {
                    "format": format_str,
                    "outtmpl": outtmpl,
                    "merge_output_format": "mp4" if ffmpeg_available else None,
                    "quiet": True,
                    "no_warnings": True,
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
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in files:
                zip_file.write(file_path, arcname=os.path.basename(file_path))
        return zip_path, temp_dir, "descarga.zip"
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
