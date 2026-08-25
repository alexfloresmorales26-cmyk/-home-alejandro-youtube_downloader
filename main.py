# -*- coding: utf-8 -*-
"""
=============================================================================
MODULO: main.py
DESCRIPCION: Interfaz de usuario interactiva y completa por consola.
=============================================================================
"""

import os
import sys
import argparse
from downloader import YouTubeDownloader, format_duration, Colors


def clear_screen():
    """Limpia la terminal según el sistema operativo."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner(output_dir: str, ffmpeg_status: bool):
    """Muestra el encabezado estilizado con estado del sistema."""
    status_ffmpeg = f"{Colors.GREEN}Disponible (Máxima resolución + Conversiones activas){Colors.END}" if ffmpeg_status else f"{Colors.YELLOW}No instalado (Descargas nativas activas){Colors.END}"
    
    print(f"""{Colors.BOLD}{Colors.CYAN}
╔════════════════════════════════════════════════════════════════╗
║             DESCARGADOR DE YOUTUBE PROFESIONAL (Python)        ║
╚════════════════════════════════════════════════════════════════╝{Colors.END}
  📁 Carpeta destino : {Colors.BOLD}{output_dir}{Colors.END}
  ⚙️  Motor FFmpeg    : {status_ffmpeg}
""")


def show_video_details(info: dict):
    """Muestra la información detallada del video."""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}--- Información del Contenido ---{Colors.END}")
    print(f"{Colors.BOLD}Título    :{Colors.END} {info.get('title', 'N/A')}")
    print(f"{Colors.BOLD}Canal     :{Colors.END} {info.get('uploader', 'N/A')}")
    print(f"{Colors.BOLD}Duración  :{Colors.END} {format_duration(info.get('duration'))}")
    vistas = info.get('view_count')
    print(f"{Colors.BOLD}Vistas    :{Colors.END} {vistas:,}" if vistas else f"{Colors.BOLD}Vistas    :{Colors.END} N/A")
    print(f"{Colors.YELLOW}----------------------------------{Colors.END}\n")


def interactive_mode(downloader: YouTubeDownloader):
    """Menú principal interactivo."""
    while True:
        clear_screen()
        print_banner(downloader.output_dir, downloader.has_ffmpeg)

        print(f"{Colors.BOLD}Selecciona una opción:{Colors.END}")
        print(f"  {Colors.GREEN}1.{Colors.END} Descargar Video (Máxima Calidad)")
        print(f"  {Colors.GREEN}2.{Colors.END} Descargar Video (Elegir Resolución: 1080p, 720p, etc.)")
        print(f"  {Colors.GREEN}3.{Colors.END} Descargar solo Audio (MP3, M4A, WAV, FLAC)")
        print(f"  {Colors.GREEN}4.{Colors.END} Descargar Lista de Reproducción (Playlist)")
        print(f"  {Colors.GREEN}5.{Colors.END} Descargar Miniatura del Video (Thumbnail)")
        print(f"  {Colors.GREEN}6.{Colors.END} Descargar Subtítulos (.vtt / .srt)")
        print(f"  {Colors.GREEN}7.{Colors.END} Ver información del Video")
        print(f"  {Colors.GREEN}8.{Colors.END} Cambiar carpeta de descargas")
        print(f"  {Colors.RED}9.{Colors.END} Salir")
        print()

        choice = input(f"{Colors.BOLD}Opción [1-9]: {Colors.END}").strip()

        if choice == "9":
            print(f"\n{Colors.GREEN}¡Gracias por usar el descargador! Hasta pronto.{Colors.END}\n")
            break

        if choice == "8":
            new_path = input("\nIngresa la nueva ruta para guardar las descargas: ").strip()
            if new_path:
                downloader.output_dir = os.path.abspath(new_path)
                os.makedirs(downloader.output_dir, exist_ok=True)
                print(f"{Colors.GREEN}✓ Carpeta actualizada a: {downloader.output_dir}{Colors.END}")
            input("\nPresiona Enter para continuar...")
            continue

        if choice not in ["1", "2", "3", "4", "5", "6", "7"]:
            print(f"\n{Colors.RED}[!] Opción inválida. Intenta nuevamente.{Colors.END}")
            input("Presiona Enter para continuar...")
            continue

        url = input(f"\n{Colors.BOLD}Ingresa la URL de YouTube:{Colors.END} ").strip()
        if not url:
            print(f"\n{Colors.RED}[!] La URL no puede estar vacía.{Colors.END}")
            input("Presiona Enter para continuar...")
            continue

        try:
            # 1. Video máxima calidad
            if choice == "1":
                print(f"\n{Colors.CYAN}Obteniendo información del video...{Colors.END}")
                info = downloader.get_info(url)
                show_video_details(info)
                print(f"{Colors.BOLD}Iniciando descarga en máxima calidad...{Colors.END}")
                ok = downloader.download_video(url)
                if ok:
                    print(f"\n{Colors.GREEN}✓ Video guardado exitosamente en: {downloader.output_dir}{Colors.END}\n")

            # 2. Video con resolución personalizada
            elif choice == "2":
                print(f"\n{Colors.CYAN}Buscando resoluciones disponibles...{Colors.END}")
                resolutions = downloader.get_available_resolutions(url)
                if not resolutions:
                    resolutions = ["1080p", "720p", "480p", "360p"]

                print(f"\n{Colors.BOLD}Resoluciones disponibles:{Colors.END}")
                for idx, res in enumerate(resolutions, 1):
                    print(f"  {Colors.GREEN}{idx}.{Colors.END} {res}")

                res_choice = input(f"\n{Colors.BOLD}Elige resolución [1-{len(resolutions)}]: {Colors.END}").strip()
                selected_res = None
                if res_choice.isdigit() and 1 <= int(res_choice) <= len(resolutions):
                    selected_res = resolutions[int(res_choice) - 1]
                else:
                    print(f"{Colors.YELLOW}[!] Opción no válida. Se usará la mejor resolución disponible.{Colors.END}")

                print(f"\n{Colors.BOLD}Descargando en {selected_res or 'máxima calidad'}...{Colors.END}")
                ok = downloader.download_video(url, resolution=selected_res)
                if ok:
                    print(f"\n{Colors.GREEN}✓ Video guardado exitosamente en: {downloader.output_dir}{Colors.END}\n")

            # 3. Descargar solo audio
            elif choice == "3":
                print(f"\n{Colors.CYAN}Formatos de audio disponibles:{Colors.END}")
                print("  1. MP3 (Recomendado)")
                print("  2. M4A")
                print("  3. WAV")
                print("  4. FLAC")
                fmt_choice = input("Elige formato [1-4] (default 1): ").strip()
                fmt_map = {"1": "mp3", "2": "m4a", "3": "wav", "4": "flac"}
                audio_fmt = fmt_map.get(fmt_choice, "mp3")

                print(f"\n{Colors.CYAN}Obteniendo información del video...{Colors.END}")
                info = downloader.get_info(url)
                show_video_details(info)
                print(f"{Colors.BOLD}Iniciando descarga de audio ({audio_fmt.upper()})...{Colors.END}")
                ok = downloader.download_audio(url, audio_format=audio_fmt)
                if ok:
                    print(f"\n{Colors.GREEN}✓ Audio guardado exitosamente en: {downloader.output_dir}{Colors.END}\n")

            # 4. Playlist
            elif choice == "4":
                print(f"\n{Colors.BOLD}Opciones de la lista de reproducción:{Colors.END}")
                print("  1. Descargar videos completos")
                print("  2. Descargar solo audios (MP3)")
                pl_choice = input("Elige opción [1-2] (default 1): ").strip()
                audio_only = (pl_choice == "2")

                print(f"\n{Colors.BOLD}Iniciando descarga de la playlist...{Colors.END}")
                ok = downloader.download_playlist(url, audio_only=audio_only)
                if ok:
                    print(f"\n{Colors.GREEN}✓ Playlist descargada exitosamente en: {downloader.output_dir}{Colors.END}\n")

            # 5. Miniatura
            elif choice == "5":
                print(f"\n{Colors.CYAN}Descargando miniatura en alta resolución...{Colors.END}")
                ok = downloader.download_thumbnail(url)
                if ok:
                    print(f"\n{Colors.GREEN}✓ Miniatura guardada en: {downloader.output_dir}{Colors.END}\n")

            # 6. Subtítulos
            elif choice == "6":
                print(f"\n{Colors.CYAN}Descargando subtítulos en español e inglés...{Colors.END}")
                ok = downloader.download_subtitles(url, lang="es")
                if ok:
                    print(f"\n{Colors.GREEN}✓ Subtítulos guardados en: {downloader.output_dir}{Colors.END}\n")

            # 7. Información
            elif choice == "7":
                print(f"\n{Colors.CYAN}Consultando metadatos...{Colors.END}")
                info = downloader.get_info(url)
                show_video_details(info)

        except Exception as e:
            print(f"\n{Colors.RED}[!] Ocurrió un error: {e}{Colors.END}\n")

        input(f"\n{Colors.BOLD}Presiona Enter para continuar...{Colors.END}")


def parse_args():
    """Procesa los argumentos CLI para llamadas automatizadas."""
    parser = argparse.ArgumentParser(description="Descargador avanzado de YouTube en Python")
    parser.add_argument("url", nargs="?", help="URL del video o lista de reproducción")
    parser.add_argument("-a", "--audio", action="store_true", help="Descargar únicamente el audio")
    parser.add_argument("--format", type=str, default="mp3", help="Formato de audio (mp3, m4a, wav, flac)")
    parser.add_argument("-r", "--resolution", type=str, help="Resolución (ej. 1080p, 720p, 480p)")
    parser.add_argument("-p", "--playlist", action="store_true", help="Indica que la URL es una lista de reproducción")
    parser.add_argument("-t", "--thumbnail", action="store_true", help="Descargar solo la miniatura")
    parser.add_argument("-s", "--subtitles", action="store_true", help="Descargar subtítulos")
    parser.add_argument("-o", "--output", type=str, default="downloads", help="Carpeta de destino")
    return parser.parse_args()


def main():
    args = parse_args()
    downloader = YouTubeDownloader(output_dir=args.output)

    if not args.url:
        interactive_mode(downloader)
        return

    url = args.url
    print(f"Destino: {downloader.output_dir}")

    if args.thumbnail:
        downloader.download_thumbnail(url)
    elif args.subtitles:
        downloader.download_subtitles(url)
    elif args.playlist:
        downloader.download_playlist(url, audio_only=args.audio, resolution=args.resolution)
    elif args.audio:
        downloader.download_audio(url, audio_format=args.format)
    else:
        downloader.download_video(url, resolution=args.resolution)


if __name__ == "__main__":
    main()
