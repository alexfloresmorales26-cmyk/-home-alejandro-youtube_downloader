# -*- coding: utf-8 -*-
"""
=============================================================================
MODULO: gui.py
DESCRIPCION: Lanzador de la Aplicación de Escritorio Nativa (Desktop GUI).
             Abre una ventana independiente en la pantalla del usuario.
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
from app import StandaloneWebHandler, TEMPLATES_DIR, STATIC_DIR


def find_free_port() -> int:
    """Encuentra un puerto TCP libre en el sistema."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def start_local_server(port: int):
    """Inicia el servidor local en un hilo en segundo plano."""
    server = HTTPServer(('127.0.0.1', port), StandaloneWebHandler)
    server.serve_forever()


def open_standalone_window(url: str):
    """
    Intenta abrir la URL como una ventana de aplicación nativa e independiente
    usando Chrome/Chromium/Edge en modo app, o PyWebView si está disponible.
    """
    # 1. Intentar con PyWebView si está instalado
    try:
        import webview
        print("[Desktop GUI] Iniciando con motor PyWebView...")
        webview.create_window(
            title="YouTube Downloader Pro",
            url=url,
            width=1050,
            height=750,
            resizable=True,
            min_size=(800, 600)
        )
        webview.start()
        return
    except ImportError:
        pass

    # 2. Intentar abrir en modo App Nativa con navegadores del sistema (ventana dedicada sin pestañas)
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
            print(f"[Desktop GUI] Ventana de escritorio abierta con: {cmd[0]}")
            return
        except FileNotFoundError:
            continue

    # 3. Respaldo estándar si no hay modo app disponible
    print("[Desktop GUI] Abriendo en el navegador predeterminado...")
    webbrowser.open(url)


def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║             INICIANDO APLICACIÓN DE ESCRITORIO                 ║
╚════════════════════════════════════════════════════════════════╝
    """)
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"

    # Iniciar servidor interno en segundo plano
    server_thread = threading.Thread(target=start_local_server, args=(port,), daemon=True)
    server_thread.start()
    time.sleep(0.5)

    print(f"✓ Servidor interno activo en: {url}")
    print("✓ Abriendo ventana de escritorio...")

    # Abrir ventana de escritorio
    open_standalone_window(url)


if __name__ == "__main__":
    main()
