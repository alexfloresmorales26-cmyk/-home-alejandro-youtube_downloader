# -*- coding: utf-8 -*-
"""
=============================================================================
MODULO: test_app.py
DESCRIPCION: Pruebas de regresion para validacion, cookies, API y servidor
             nativo. No realizan peticiones de red.
=============================================================================
"""

import http.client
import os
import tempfile
import threading
import time
import unittest
from unittest import mock

import cookies
from core import process_download_request, process_info_request
from utils import (
    TEMP_DIR_PREFIX,
    cleanup_temp_dirs,
    list_downloaded_files,
    pick_downloaded_file,
    validate_youtube_url,
)


class TestUrlValidation(unittest.TestCase):
    def test_valid_youtube_urls(self):
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ?si=abc",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/live/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?app=desktop&v=dQw4w9WgXcQ",
            "https://www.youtube.com/playlist?list=PL123456",
            "youtu.be/dQw4w9WgXcQ",
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                es_valido, mensaje = validate_youtube_url(url)
                self.assertTrue(es_valido)
                self.assertEqual(mensaje, "")

    def test_invalid_youtube_urls(self):
        invalid_urls = [
            "",
            "   ",
            "https://example.com/watch?v=abc",
            "https://youtube.com.evil.com/watch?v=abc",
            "https://www.youtube.com/watch",
            "https://www.youtube.com/playlist",
            "https://www.youtube.com/",
            "youtube.com",
            "javascript:alert(1)",
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                es_valido, mensaje = validate_youtube_url(url)
                self.assertFalse(es_valido)
                self.assertTrue(mensaje)

    def test_invalid_url_does_not_crash_info(self):
        result = process_info_request("https://example.com/video")
        self.assertFalse(result["success"])
        self.assertIn("YouTube", result["error"])

    def test_invalid_url_does_not_crash_download(self):
        with self.assertRaises(ValueError):
            process_download_request("https://example.com/video")


class TestCookies(unittest.TestCase):
    def test_standard_tab_separated_cookies(self):
        content = (
            "# Netscape HTTP Cookie File\n"
            ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tVISITOR_INFO1_LIVE\tabc\n"
        )
        self.assertTrue(cookies.is_netscape_cookies(content))

    def test_httponly_cookie_line(self):
        content = "#HttpOnly_.youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID\tabc\n"
        self.assertTrue(cookies.is_netscape_cookies(content))

    def test_space_separated_cookies_are_repaired(self):
        content = ".youtube.com  TRUE  /  TRUE  1893456000  VISITOR_INFO1_LIVE  abc"
        self.assertTrue(cookies.is_netscape_cookies(content))
        fixed = cookies.fix_netscape_cookies(content)
        self.assertTrue(fixed.startswith("# Netscape HTTP Cookie File"))
        self.assertIn(
            ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tVISITOR_INFO1_LIVE\tabc",
            fixed,
        )

    def test_malformed_third_party_cookie_is_dropped(self):
        content = (
            "# Netscape HTTP Cookie File\n"
            ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tVISITOR_INFO1_LIVE\tabc\n"
            "www.tiktok.com\tTRUE\t/path\tFALSE\t1794897824\tgd_random\tvalue\n"
        )
        sanitized, dropped = cookies.sanitize_netscape_cookies(content)
        self.assertEqual(dropped, 1)
        self.assertNotIn("tiktok", sanitized.lower())
        self.assertIn("youtube.com", sanitized)
        self.assertTrue(cookies.is_netscape_cookies(sanitized))

    def test_domain_flag_is_normalized_for_cookiejar(self):
        content = "www.youtube.com\tTRUE\t/\tTRUE\t1893456000\tNAME\tvalue\n"
        sanitized, _dropped = cookies.sanitize_netscape_cookies(content)
        self.assertIn(
            "www.youtube.com\tFALSE\t/\tTRUE\t1893456000\tNAME\tvalue",
            sanitized,
        )

    def test_sanitized_cookies_can_be_loaded_by_cookiejar(self):
        import http.cookiejar

        content = (
            "# Netscape HTTP Cookie File\n"
            ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tVISITOR_INFO1_LIVE\tabc\n"
            "www.tiktok.com\tTRUE\t/path\tFALSE\t1794897824\tgd_random\tvalue\n"
        )
        sanitized, _dropped = cookies.sanitize_netscape_cookies(content)

        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as cookie_file:
            cookie_file.write(sanitized)
            cookie_path = cookie_file.name

        try:
            jar = http.cookiejar.MozillaCookieJar(cookie_path)
            jar.load(ignore_discard=True, ignore_expires=True)
            self.assertGreaterEqual(len(jar), 1)
        finally:
            os.unlink(cookie_path)

    def test_invalid_cookie_content(self):
        self.assertFalse(cookies.is_netscape_cookies(""))
        self.assertFalse(cookies.is_netscape_cookies("esto no es una cookie"))

    def test_parse_browser_spec(self):
        self.assertEqual(
            cookies.parse_browser_spec("chrome"),
            ("chrome", None, None, None),
        )
        self.assertEqual(
            cookies.parse_browser_spec("firefox:default"),
            ("firefox", "default", None, None),
        )
        self.assertEqual(
            cookies.parse_browser_spec("chrome+keyring:perfil::contenedor"),
            ("chrome", "perfil", "keyring", "contenedor"),
        )
        with self.assertRaises(ValueError):
            cookies.parse_browser_spec("")

    def test_dotenv_loader(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".env", delete=False, encoding="utf-8"
        ) as env_file:
            env_file.write("TEST_YTDLP_VALUE=hola mundo\n")
            env_path = env_file.name
        try:
            os.environ.pop("TEST_YTDLP_VALUE", None)
            cookies._load_dotenv(env_path)
            self.assertEqual(os.environ["TEST_YTDLP_VALUE"], "hola mundo")
        finally:
            os.environ.pop("TEST_YTDLP_VALUE", None)
            os.unlink(env_path)


class TestTempFiles(unittest.TestCase):
    def test_cleanup_only_removes_own_prefix(self):
        with tempfile.TemporaryDirectory() as root:
            old_time = time.time() - 3 * 3600
            own_dir = os.path.join(root, TEMP_DIR_PREFIX + "propio")
            other_dir = os.path.join(root, "tmp-de-otra-app")
            os.makedirs(own_dir)
            os.makedirs(other_dir)
            os.utime(own_dir, (old_time, old_time))
            os.utime(other_dir, (old_time, old_time))

            with mock.patch("utils.tempfile.gettempdir", return_value=root):
                result = cleanup_temp_dirs(max_age_hours=2)

            self.assertFalse(os.path.exists(own_dir))
            self.assertTrue(os.path.exists(other_dir))
            self.assertEqual(result["cleaned_dirs"], 1)

    def test_list_and_pick_downloaded_files(self):
        with tempfile.TemporaryDirectory() as root:
            small = os.path.join(root, "small.mp4")
            large = os.path.join(root, "large.mp4")
            partial = os.path.join(root, "video.mp4.part")
            with open(small, "wb") as f:
                f.write(b"a" * 10)
            with open(large, "wb") as f:
                f.write(b"b" * 100)
            with open(partial, "wb") as f:
                f.write(b"c" * 1000)

            files = list_downloaded_files(root)
            self.assertCountEqual(files, [small, large])
            self.assertEqual(pick_downloaded_file(root), large)


class TestFlaskApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        if not app_module.FLASK_AVAILABLE:
            raise unittest.SkipTest("Flask no esta instalado")
        cls.client = app_module.app.test_client()

    def test_info_invalid_url_returns_400(self):
        response = self.client.post(
            "/api/info", json={"url": "https://example.com/video"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_download_head_invalid_url_returns_400(self):
        response = self.client.head(
            "/api/download?url=https%3A%2F%2Fexample.com%2Fvideo"
        )
        self.assertEqual(response.status_code, 400)

    def test_download_head_valid_url_returns_200_without_downloading(self):
        response = self.client.head(
            "/api/download?url=https%3A%2F%2Fyoutu.be%2FdQw4w9WgXcQ"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Length"), "0")

    def test_cookies_status(self):
        response = self.client.get("/api/cookies-status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("cookies_configured", data)
        self.assertIn("cookies_valid", data)
        self.assertIn("ffmpeg_available", data)


class TestNativeServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer

        from app import StandaloneWebHandler

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), StandaloneWebHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _request(self, method, path):
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        try:
            conn.request(method, path)
            response = conn.getresponse()
            response.read()
            return response.status
        finally:
            conn.close()

    def test_native_head_valid_url(self):
        status = self._request(
            "HEAD", "/api/download?url=https%3A%2F%2Fyoutu.be%2FdQw4w9WgXcQ"
        )
        self.assertEqual(status, 200)

    def test_native_head_invalid_url(self):
        status = self._request(
            "HEAD", "/api/download?url=https%3A%2F%2Fexample.com%2Fvideo"
        )
        self.assertEqual(status, 400)

    def test_native_index(self):
        self.assertEqual(self._request("GET", "/"), 200)


if __name__ == "__main__":
    unittest.main()
