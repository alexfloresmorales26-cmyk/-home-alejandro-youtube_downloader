# -*- coding: utf-8 -*-
"""
=============================================================================
MODULO: downloader.py
DESCRIPCION: Motor principal de descarga con yt-dlp.
             Soporta video, audio, miniaturas, subtítulos y listas de reproducción.
             Usa cadenas de formato robustas con múltiples niveles de respaldo.
=============================================================================
"""

import os
import sys
import shutil
from typing import Optional, Dict, Any, Callable, List
import yt_dlp


# Códigos de colores ANSI para la consola
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def format_bytes(size_bytes: Optional[int]) -> str:
    """Convierte bytes a formato legible (KB, MB, GB)."""
    if not size_bytes:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_duration(seconds: Optional[int]) -> str:
    """Convierte segundos a formato HH:MM:SS o MM:SS."""
    if not seconds:
        return "Desconocida"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def has_ffmpeg() -> bool:
    """Comprueba si ffmpeg está instalado en el sistema."""
    return shutil.which("ffmpeg") is not None


def _build_video_format(height: Optional[str] = None, ffmpeg: bool = False) -> str:
    """
    Construye la cadena de formato de video con múltiples niveles de respaldo
    para garantizar que siempre haya un formato disponible.
    """
    if height:
        if ffmpeg:
            return (
                f"bestvideo[height={height}][ext=mp4]+bestaudio[ext=m4a]"
                f"/bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]"
                f"/bestvideo[height<={height}]+bestaudio"
                f"/best[height<={height}]"
                f"/bestvideo+bestaudio"
                f"/best"
            )
        else:
            return (
                f"best[height={height}][ext=mp4]"
                f"/best[height<={height}][ext=mp4]"
                f"/best[height<={height}]"
                f"/best"
            )
    else:
        if ffmpeg:
            return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        else:
            return "best[ext=mp4]/best"


class YouTubeDownloader:
    """
    Gestor completo para descargas de YouTube:
    - Videos (máxima calidad o resolución elegida)
    - Audios (MP3, M4A, WAV, FLAC)
    - Playlists organizadas en carpetas
    - Miniaturas en alta resolución
    - Subtítulos
    """

    def __init__(self, output_dir: str = "downloads"):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.has_ffmpeg = has_ffmpeg()

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """Muestra el progreso con barra visual y estadísticas en tiempo real."""
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            percent = (downloaded / total * 100) if total > 0 else 0
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0

            speed_str = f"{format_bytes(speed)}/s" if speed else "N/A"
            eta_str = f"{int(eta)}s" if eta else "N/A"
            downloaded_str = format_bytes(downloaded)
            total_str = format_bytes(total) if total else "N/A"

            bar_len = 25
            filled_len = int(bar_len * percent // 100)
            bar = "█" * filled_len + "░" * (bar_len - filled_len)

            sys.stdout.write(
                f"\r  {Colors.CYAN}[{bar}] {percent:5.1f}%{Colors.END} | "
                f"{Colors.YELLOW}{downloaded_str}/{total_str}{Colors.END} | "
                f"Vel: {Colors.GREEN}{speed_str}{Colors.END} | "
                f"ETA: {Colors.BLUE}{eta_str}{Colors.END}   "
            )
            sys.stdout.flush()

        elif status == "finished":
            sys.stdout.write(
                f"\n  {Colors.GREEN}✓ Descarga completada. Guardando archivo...{Colors.END}\n"
            )
            sys.stdout.flush()

    def get_info(self, url: str) -> Dict[str, Any]:
        """Obtiene metadatos del video o lista sin descargarlo."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def get_available_resolutions(self, url: str) -> List[str]:
        """Obtiene las resoluciones de video disponibles ordenadas de mayor a menor."""
        info = self.get_info(url)
        formats = info.get("formats", [])
        heights = set()

        for f in formats:
            if f.get("vcodec") != "none" and f.get("height"):
                heights.add(f["height"])

        sorted_heights = sorted(list(heights), reverse=True)
        return [f"{h}p" for h in sorted_heights]

    def download_video(
        self,
        url: str,
        resolution: Optional[str] = None,
        download_subtitles: bool = False,
    ) -> bool:
        """Descarga el video en la mejor calidad o resolución especificada."""
        outtmpl = os.path.join(self.output_dir, "%(title)s.%(ext)s")
        height = resolution.replace("p", "") if resolution else None
        format_str = _build_video_format(height=height, ffmpeg=self.has_ffmpeg)

        ydl_opts = {
            "format": format_str,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4" if self.has_ffmpeg else None,
            "progress_hooks": [self._progress_hook],
            "no_warnings": True,
            "quiet": True,
        }

        if download_subtitles:
            ydl_opts.update(
                {
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": ["es", "en"],
                }
            )

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            print(f"\n{Colors.RED}[Error al descargar video]: {e}{Colors.END}")
            return False

    def download_audio(
        self, url: str, audio_format: str = "mp3", quality: str = "192"
    ) -> bool:
        """Descarga y convierte el audio a MP3, M4A, WAV o FLAC."""
        outtmpl = os.path.join(self.output_dir, "%(title)s.%(ext)s")

        if self.has_ffmpeg:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": audio_format,
                        "preferredquality": quality,
                    }
                ],
                "progress_hooks": [self._progress_hook],
                "no_warnings": True,
                "quiet": True,
            }
        else:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "progress_hooks": [self._progress_hook],
                "no_warnings": True,
                "quiet": True,
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            print(f"\n{Colors.RED}[Error al descargar audio]: {e}{Colors.END}")
            return False

    def download_playlist(
        self, url: str, audio_only: bool = False, resolution: Optional[str] = None
    ) -> bool:
        """Descarga una lista de reproducción completa en su propia subcarpeta."""
        outtmpl = os.path.join(
            self.output_dir,
            "%(playlist_title)s",
            "%(playlist_index)02d - %(title)s.%(ext)s",
        )

        postprocessors = []
        if audio_only:
            format_str = "bestaudio/best"
            if self.has_ffmpeg:
                postprocessors.append(
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                )
        else:
            height = resolution.replace("p", "") if resolution else None
            format_str = _build_video_format(height=height, ffmpeg=self.has_ffmpeg)

        ydl_opts = {
            "format": format_str,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4"
            if (not audio_only and self.has_ffmpeg)
            else None,
            "postprocessors": postprocessors,
            "progress_hooks": [self._progress_hook],
            "no_warnings": True,
            "quiet": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            print(f"\n{Colors.RED}[Error al descargar playlist]: {e}{Colors.END}")
            return False

    def download_thumbnail(self, url: str) -> bool:
        """Descarga la miniatura del video en máxima resolución."""
        outtmpl = os.path.join(self.output_dir, "%(title)s.%(ext)s")
        ydl_opts = {
            "writethumbnail": True,
            "skip_download": True,
            "outtmpl": outtmpl,
            "no_warnings": True,
            "quiet": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            print(f"\n{Colors.RED}[Error al descargar miniatura]: {e}{Colors.END}")
            return False

    def download_subtitles(self, url: str, lang: str = "es") -> bool:
        """Descarga los subtítulos del video."""
        outtmpl = os.path.join(self.output_dir, "%(title)s.%(ext)s")
        ydl_opts = {
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [lang],
            "skip_download": True,
            "outtmpl": outtmpl,
            "no_warnings": True,
            "quiet": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            print(f"\n{Colors.RED}[Error al descargar subtítulos]: {e}{Colors.END}")
            return False
