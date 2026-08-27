# -*- coding: utf-8 -*-
"""
=============================================================================
MODULO: gui.py
DESCRIPCION: Lanzador de la Aplicación de Escritorio Nativa (Desktop GUI).
             Mantiene el servidor web activo y abre la ventana independiente.
=============================================================================
"""

import os
import sys
import time
import socket
import threading
import subprocess
import webbrowser
from http.server import HTTPServer
from app import StandaloneWebHandler


def find_free_port(default_port: int = 5000) -> int:
    """Intenta usar el puerto por defecto o busca uno libre."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", default_port))
            return default_port
    except OSError:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def open_desktop_window(url: str):
    """Abre la ventana de la aplicación de escritorio."""
    time.sleep(0.8)  # Dar tiempo a que el servidor esté escuchando peticiones

    # 1. Modo nativo con navegadores del sistema (Ventana sin barras de navegador)
    browsers = [
        ["google-chrome", f"--app={url}", "--window-size=1050,750"],
        ["chromium-browser", f"--app={url}", "--window-size=1050,750"],
        ["chromium", f"--app={url}", "--window-size=1050,750"],
        ["microsoft-edge", f"--app={url}", "--window-size=1050,750"],
        ["brave-browser", f"--app={url}", "--window-size=1050,750"],
    ]

    for cmd in browsers:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"✓ Ventana de escritorio iniciada con: {cmd[0]}")
            return
        except FileNotFoundError:
            continue

    # 2. Respaldo abriendo en el navegador predeterminado
    print("✓ Abriendo en el navegador predeterminado...")
    webbrowser.open(url)


def main():
    print(
        """
╔════════════════════════════════════════════════════════════════╗
║             DESCARGADOR DE YOUTUBE - MODO ESCRITORIO           ║
╚════════════════════════════════════════════════════════════════╝
    """
    )
    port = find_free_port(5000)
    url = f"http://127.0.0.1:{port}"
    # Crear servidor HTTP local
    server = HTTPServer(("127.0.0.1", port), StandaloneWebHandler)

    print(f"✓ Servidor local iniciado en: {url}")
    print("✓ Abriendo interfaz gráfica...")
    print("\n[INFO] Deja esta terminal abierta mientras uses la aplicación.")
    print("[INFO] Para cerrar la aplicación, presiona Ctrl + C en esta terminal.\n")

    # Lanzar la ventana en un hilo secundario mientras el servidor corre en el hilo principal
    threading.Thread(target=open_desktop_window, args=(url,), daemon=True).start()

    # Mantener el servidor escuchando de forma indefinida
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nCerrando aplicación... ¡Hasta pronto!")
        server.server_close()


if __name__ == "__main__":
    main()
