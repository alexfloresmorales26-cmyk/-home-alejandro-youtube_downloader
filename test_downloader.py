# -*- coding: utf-8 -*-
"""
=============================================================================
MODULO: test_downloader.py
DESCRIPCION: Suite de pruebas unitarias para validar las funciones del descargador.
=============================================================================
"""

import unittest
from downloader import (
    YouTubeDownloader,
    format_bytes,
    format_duration,
    has_ffmpeg,
    Colors,
)


class TestYouTubeDownloader(unittest.TestCase):
    def test_format_bytes(self):
        """Verifica la conversión de bytes a unidades legibles."""
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(1024 * 1024), "1.00 MB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024), "1.00 GB")

    def test_format_duration(self):
        """Verifica el formateo de segundos a tiempo estructurado."""
        self.assertEqual(format_duration(0), "Desconocida")
        self.assertEqual(format_duration(45), "00:45")
        self.assertEqual(format_duration(125), "02:05")
        self.assertEqual(format_duration(3665), "01:01:05")

    def test_downloader_initialization(self):
        """Verifica la correcta inicialización del directorio de descargas."""
        dl = YouTubeDownloader(output_dir="downloads")
        self.assertTrue(dl.output_dir.endswith("downloads"))
        self.assertIsInstance(dl.has_ffmpeg, bool)

    def test_colors_presence(self):
        """Verifica que las constantes de formato ANSI existan."""
        self.assertTrue(hasattr(Colors, "GREEN"))
        self.assertTrue(hasattr(Colors, "CYAN"))
        self.assertTrue(hasattr(Colors, "END"))


if __name__ == "__main__":
    unittest.main()
