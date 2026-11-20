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

import core
import cookies
from core import (
    _normalize_download_options,
    _video_height,
    process_download_request,
    process_info_request,
)
from downloader import _build_video_format
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

    def test_youtu_be_rejects_extra_path_segments(self):
        self.assertFalse(validate_youtube_url("https://youtu.be/abc/def")[0])
        self.assertTrue(validate_youtube_url("https://youtu.be/abc")[0])

    def test_invalid_url_does_not_crash_info(self):
        result = process_info_request("https://example.com/video")
        self.assertFalse(result["success"])
        self.assertIn("YouTube", result["error"])

    def test_invalid_url_does_not_crash_download(self):
        with self.assertRaises(ValueError):
            process_download_request("https://example.com/video")


class TestDownloadOptions(unittest.TestCase):
    def setUp(self):
        core.clear_info_cache()

    def test_invalid_type_falls_back_to_video(self):
        self.assertEqual(
            _normalize_download_options("../etc", "best"), ("video", "best")
        )
        self.assertEqual(_normalize_download_options(None, None), ("video", "best"))

    def test_invalid_audio_format_falls_back_to_mp3(self):
        self.assertEqual(
            _normalize_download_options("audio", "1080p"), ("audio", "mp3")
        )
        self.assertEqual(
            _normalize_download_options("audio", "FLAC"), ("audio", "flac")
        )

    def test_invalid_video_quality_falls_back_to_best(self):
        self.assertEqual(
            _normalize_download_options("video", "720p]&x=1"), ("video", "best")
        )
        self.assertEqual(
            _normalize_download_options("video", "1080p"), ("video", "1080p")
        )

    def test_video_height_validation(self):
        self.assertEqual(_video_height("1080p"), "1080")
        self.assertIsNone(_video_height("0p"))
        self.assertIsNone(_video_height("abc"))
        self.assertIsNone(_video_height("1080"))

    def test_info_forces_single_video_and_timeout(self):
        fake_info = {"title": "Video", "formats": []}
        with mock.patch("core.yt_dlp.YoutubeDL") as ydl_cls:
            ydl_cls.return_value.__enter__.return_value.extract_info.return_value = (
                fake_info
            )
            result = process_info_request(
                "https://www.youtube.com/watch?v=abc&list=PL123"
            )
        opts = ydl_cls.call_args[0][0]
        self.assertTrue(opts.get("noplaylist"))
        self.assertEqual(opts.get("socket_timeout"), 30)
        self.assertTrue(result["success"])

    def test_download_forces_single_video_and_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_file = os.path.join(tmp, "video.mp4")
            with open(fake_file, "wb") as handle:
                handle.write(b"x")
            with mock.patch("core.yt_dlp.YoutubeDL") as ydl_cls, mock.patch(
                "core.tempfile.mkdtemp", return_value=tmp
            ), mock.patch("core.list_downloaded_files", return_value=[fake_file]):
                process_download_request(
                    "https://www.youtube.com/watch?v=abc&list=PL123",
                    "video",
                    "1080p",
                )
        opts = ydl_cls.call_args[0][0]
        self.assertTrue(opts.get("noplaylist"))
        self.assertEqual(opts.get("socket_timeout"), 30)

    def test_format_string_never_contains_invalid_height(self):
        self.assertNotIn("abc", _build_video_format("abc", ffmpeg=True))
        self.assertNotIn("height=0", _build_video_format("0", ffmpeg=True))
        self.assertIn("height=720", _build_video_format("720", ffmpeg=True))


class TestInfoCache(unittest.TestCase):
    def setUp(self):
        core.clear_info_cache()

    def tearDown(self):
        core.clear_info_cache()

    @staticmethod
    def _fake_info():
        return {
            "title": "Video de prueba",
            "formats": [{"height": 720, "vcodec": "avc1"}],
            "view_count": 10,
        }

    def test_info_cache_reuses_result_and_returns_copies(self):
        with mock.patch("core.yt_dlp.YoutubeDL") as ydl_cls:
            ydl_cls.return_value.__enter__.return_value.extract_info.return_value = (
                self._fake_info()
            )
            first = process_info_request("https://youtu.be/cachehit")
            first["title"] = "mutado"
            second = process_info_request("https://youtu.be/cachehit")

        self.assertEqual(ydl_cls.call_count, 1)
        self.assertEqual(second["title"], "Video de prueba")

    def test_info_cache_can_be_disabled(self):
        with mock.patch.object(core, "INFO_CACHE_TTL", 0):
            with mock.patch("core.yt_dlp.YoutubeDL") as ydl_cls:
                extract = ydl_cls.return_value.__enter__.return_value.extract_info
                extract.return_value = self._fake_info()
                process_info_request("https://youtu.be/cacheoff")
                process_info_request("https://youtu.be/cacheoff")

        self.assertEqual(ydl_cls.call_count, 2)

    def test_info_cache_evicts_oldest_entry(self):
        with mock.patch.object(core, "INFO_CACHE_MAX", 2):
            with mock.patch("core.yt_dlp.YoutubeDL") as ydl_cls:
                extract = ydl_cls.return_value.__enter__.return_value.extract_info
                extract.return_value = self._fake_info()
                for video_id in ("uno", "dos", "tres"):
                    process_info_request(f"https://youtu.be/{video_id}")
                process_info_request("https://youtu.be/uno")

        self.assertEqual(ydl_cls.call_count, 4)

    def test_info_cache_expires_after_ttl(self):
        clock = [0.0]
        with mock.patch.object(core, "INFO_CACHE_TTL", 10), mock.patch(
            "core.time.monotonic", side_effect=lambda: clock[0]
        ), mock.patch("core.yt_dlp.YoutubeDL") as ydl_cls:
            extract = ydl_cls.return_value.__enter__.return_value.extract_info
            extract.return_value = self._fake_info()
            process_info_request("https://youtu.be/cacheexpire")
            clock[0] = 9.0
            process_info_request("https://youtu.be/cacheexpire")
            clock[0] = 11.0
            process_info_request("https://youtu.be/cacheexpire")

        self.assertEqual(ydl_cls.call_count, 2)

    def test_info_cache_does_not_store_failures(self):
        with mock.patch("core.yt_dlp.YoutubeDL") as ydl_cls:
            extract = ydl_cls.return_value.__enter__.return_value.extract_info
            extract.side_effect = RuntimeError("fallo de red")
            first = process_info_request("https://youtu.be/cachefail")
            second = process_info_request("https://youtu.be/cachefail")

        self.assertFalse(first["success"])
        self.assertFalse(second["success"])
        self.assertEqual(ydl_cls.call_count, 2)


class TestDownloadConcurrency(unittest.TestCase):
    def test_semaphore_limits_concurrent_downloads(self):
        first_entered = threading.Event()
        release_first = threading.Event()
        second_entered = threading.Event()
        calls = []

        def fake_download(url, download_type, quality):
            calls.append(url)
            if len(calls) == 1:
                first_entered.set()
                release_first.wait(timeout=5)
            else:
                second_entered.set()
            return "/tmp/fake", "/tmp/fake", "fake"

        with mock.patch.object(
            core, "_DOWNLOAD_SEMAPHORE", threading.BoundedSemaphore(1)
        ), mock.patch.object(core, "_download_to_temp", side_effect=fake_download):
            first = threading.Thread(
                target=process_download_request,
                args=("https://youtu.be/dQw4w9WgXcQ",),
            )
            first.start()
            self.assertTrue(first_entered.wait(timeout=5))
            second = threading.Thread(
                target=process_download_request,
                args=("https://youtu.be/dQw4w9WgXcQ",),
            )
            second.start()
            self.assertFalse(second_entered.wait(timeout=0.2))
            release_first.set()
            first.join(timeout=5)
            second.join(timeout=5)

        self.assertTrue(second_entered.is_set())
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())


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

    def test_cookie_options_use_independent_streams(self):
        content = (
            "# Netscape HTTP Cookie File\n"
            ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID\tabc\n"
        )
        with mock.patch.object(cookies, "_COOKIES_CONTENT_SANITIZED", content):
            first = cookies.ydl_opts_with_cookies({})["cookiefile"]
            second = cookies.ydl_opts_with_cookies({})["cookiefile"]

        self.assertIsNot(first, second)
        self.assertEqual(first.getvalue(), content)
        self.assertEqual(second.getvalue(), content)

    def test_cookies_status_does_not_expose_paths(self):
        status = cookies.cookies_status()
        self.assertNotIn("cookies_path", status)
        self.assertNotIn("cookies_file", status)
        self.assertNotIn("cookies_file_configured", status)
        self.assertNotIn("cookies_source", status)
        self.assertIn("cookies_configured", status)

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

    def test_cleanup_keeps_active_downloads(self):
        with tempfile.TemporaryDirectory() as root:
            old_time = time.time() - 3 * 3600
            active_dir = os.path.join(root, TEMP_DIR_PREFIX + "activo")
            stale_dir = os.path.join(root, TEMP_DIR_PREFIX + "viejo")
            os.makedirs(active_dir)
            os.makedirs(stale_dir)

            active_part = os.path.join(active_dir, "video.mp4.part")
            with open(active_part, "wb") as f:
                f.write(b"datos en curso")
            os.utime(active_dir, (old_time, old_time))

            stale_file = os.path.join(stale_dir, "video.mp4")
            with open(stale_file, "wb") as f:
                f.write(b"resto viejo")
            os.utime(stale_dir, (old_time, old_time))
            os.utime(stale_file, (old_time, old_time))

            with mock.patch("utils.tempfile.gettempdir", return_value=root):
                result = cleanup_temp_dirs(max_age_hours=2)

            self.assertTrue(os.path.exists(active_dir))
            self.assertFalse(os.path.exists(stale_dir))
            self.assertEqual(result["cleaned_dirs"], 1)

    def test_list_downloaded_files_ignores_empty_files(self):
        with tempfile.TemporaryDirectory() as root:
            empty = os.path.join(root, "vacio.mp4")
            valid = os.path.join(root, "video.mp4")
            open(empty, "wb").close()
            with open(valid, "wb") as f:
                f.write(b"contenido")

            self.assertEqual(list_downloaded_files(root), [valid])

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

    def test_info_non_object_json_returns_400(self):
        response = self.client.post(
            "/api/info", data="[]", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_download_non_object_json_returns_400(self):
        response = self.client.post(
            "/api/download", data="[]", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_cookies_status_hides_paths(self):
        data = self.client.get("/api/cookies-status").get_json()
        self.assertNotIn("cookies_path", data)
        self.assertNotIn("cookies_file", data)
        self.assertNotIn("cookies_file_configured", data)
        self.assertNotIn("cookies_source", data)
        self.assertIn("cookies_configured", data)

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

    def test_index_uses_local_tailwind(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/static/css/tailwind.min.css", response.data)
        self.assertNotIn(b"cdn.tailwindcss.com", response.data)


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

    def _request_response(self, method, path, headers=None):
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        try:
            conn.request(method, path, headers=headers or {})
            response = conn.getresponse()
            body = response.read()
            return response.status, response.headers, body
        finally:
            conn.close()

    def _request(self, method, path):
        status, _headers, _body = self._request_response(method, path)
        return status

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

    def test_native_cookies_status(self):
        self.assertEqual(self._request("GET", "/api/cookies-status"), 200)

    def test_native_uses_http_11(self):
        handler = self.server.RequestHandlerClass
        self.assertEqual(handler.protocol_version, "HTTP/1.1")

    def test_native_static_cache_headers_and_304(self):
        status, headers, body = self._request_response("GET", "/static/css/styles.css")
        self.assertEqual(status, 200)
        self.assertTrue(body)
        self.assertIn("max-age", headers.get("Cache-Control", ""))
        last_modified = headers.get("Last-Modified")
        self.assertTrue(last_modified)

        status, headers, body = self._request_response(
            "GET",
            "/static/css/styles.css",
            {"If-Modified-Since": last_modified},
        )
        self.assertEqual(status, 304)
        self.assertEqual(body, b"")

        status, _headers, _body = self._request_response(
            "GET",
            "/static/css/styles.css",
            {"If-Modified-Since": "fecha invalida"},
        )
        self.assertEqual(status, 200)

    def test_native_json_is_not_stored(self):
        status, headers, _body = self._request_response("GET", "/api/cookies-status")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Cache-Control"), "no-store")

    def test_native_download_head_is_not_stored(self):
        status, headers, body = self._request_response(
            "HEAD", "/api/download?url=https%3A%2F%2Fyoutu.be%2FdQw4w9WgXcQ"
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertEqual(body, b"")

    def test_native_index_is_revalidated(self):
        status, headers, _body = self._request_response("GET", "/")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Cache-Control"), "no-cache")

    def test_native_security_headers_on_index(self):
        status, headers, _body = self._request_response("GET", "/")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(headers.get("Referrer-Policy"), "no-referrer")
        self.assertIn(
            "frame-ancestors 'none'", headers.get("Content-Security-Policy", "")
        )

    def test_native_security_headers_on_download_head(self):
        status, headers, body = self._request_response(
            "HEAD", "/api/download?url=https%3A%2F%2Fyoutu.be%2FdQw4w9WgXcQ"
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(headers.get("Referrer-Policy"), "no-referrer")

    def test_core_options_do_not_use_remote_components(self):
        """Las opciones de yt-dlp no deben forzar componentes remotos de GitHub."""
        import core as core_module

        source = open(core_module.__file__, "r", encoding="utf-8").read()
        self.assertNotIn("remote_components", source)

        import downloader as downloader_module

        source = open(downloader_module.__file__, "r", encoding="utf-8").read()
        self.assertNotIn("remote_components", source)


if __name__ == "__main__":
    unittest.main()
