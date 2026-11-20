# -*- coding: utf-8 -*-
"""
=============================================================================
MODULO: cookies.py
DESCRIPCION: Carga y validacion centralizada de cookies para yt-dlp.

Fuentes soportadas (en orden de prioridad):
  1. YTDLP_COOKIES        -> contenido completo del archivo cookies.txt
  2. YTDLP_COOKIES_FILE   -> ruta a un archivo cookies.txt
  3. YTDLP_COOKIES_FROM_BROWSER -> navegador del que extraer las cookies

El archivo .env de la raiz del proyecto se carga automaticamente (sin
dependencias externas) para que la configuracion local funcione al ejecutar
app.py, gui.py o main.py desde cualquier directorio.
=============================================================================
"""

import atexit
import io
import os
import re
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Carga de .env (implementacion minima, sin python-dotenv)
# ---------------------------------------------------------------------------
def _load_dotenv(path: str) -> None:
    """Carga variables KEY=VALUE de un archivo .env sin sobrescribir el entorno."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export ") :].strip()
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                if key:
                    os.environ.setdefault(key, value)
    except OSError:
        pass


_load_dotenv(os.path.join(BASE_DIR, ".env"))


# ---------------------------------------------------------------------------
# Configuracion de cookies
# ---------------------------------------------------------------------------
COOKIES_FILE = os.environ.get("YTDLP_COOKIES_FILE", "").strip()
COOKIES_CONTENT = os.environ.get("YTDLP_COOKIES", "")
COOKIES_FROM_BROWSER = os.environ.get("YTDLP_COOKIES_FROM_BROWSER", "").strip()

COOKIES_PATH: str | None = None
COOKIES_VALID = False
COOKIES_ERROR = ""
COOKIES_SOURCE = "none"
COOKIES_FROM_BROWSER_SPEC: tuple[str, str | None, str | None, str | None] | None = None

_TEMP_COOKIE_FILES: list[str] = []
_COOKIES_CONTENT_SANITIZED = ""


def _cleanup_temp_cookie_files() -> None:
    """Elimina las copias temporales de cookies al terminar el proceso."""
    for path in _TEMP_COOKIE_FILES:
        try:
            os.remove(path)
        except OSError:
            pass
    _TEMP_COOKIE_FILES.clear()


atexit.register(_cleanup_temp_cookie_files)


def _resolve_path(path: str) -> str:
    """Resuelve rutas relativas contra la raiz del proyecto (no contra el CWD)."""
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    return os.path.abspath(path)


if COOKIES_FILE:
    COOKIES_FILE = _resolve_path(COOKIES_FILE)


def _cookie_fields(line: str) -> tuple[str, list[str]]:
    """Separa una linea de cookies Netscape conservando el prefijo #HttpOnly_.

    El formato estandar usa tabuladores, pero algunos editores convierten los
    tabuladores en espacios. Se toleran ambos casos.
    """
    prefix = ""
    if line.startswith("#HttpOnly_"):
        prefix = "#HttpOnly_"
        line = line[len(prefix) :]

    fields = line.split("\t")
    if len(fields) < 7:
        fields = [field for field in re.split(r"\s{2,}", line.strip()) if field]
    if len(fields) < 7:
        fields = line.split()

    return prefix, fields


# Dominios relevantes para YouTube. Filtrar evita que una cookie corrupta de
# otro sitio invalide todo el archivo al cargarlo con http.cookiejar.
ALLOWED_COOKIE_DOMAINS = (
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "google.com",
    "googlevideo.com",
    "googleusercontent.com",
    "googleapis.com",
    "gstatic.com",
    "ytimg.com",
    "ggpht.com",
)


def _domain_allowed(domain: str) -> bool:
    normalized = domain.lstrip(".").lower()
    return any(
        normalized == allowed or normalized.endswith("." + allowed)
        for allowed in ALLOWED_COOKIE_DOMAINS
    )


def _normalize_cookie_line(line: str, filter_domains: bool = True) -> str | None:
    """Normaliza una linea Netscape y descarta la que http.cookiejar rechazaria."""
    prefix, fields = _cookie_fields(line.strip())
    if len(fields) < 7:
        return None

    domain = fields[0].strip()
    include_subdomains = fields[1].strip().upper()
    cookie_path = fields[2].strip() or "/"
    secure = fields[3].strip().upper()
    expires = fields[4].strip()
    name = fields[5].strip()
    # http.cookiejar exige exactamente 7 campos separados por tabuladores.
    value = " ".join(field.strip() for field in fields[6:])

    if not domain:
        return None
    if filter_domains and not _domain_allowed(domain):
        return None

    # http.cookiejar valida que el flag coincida con el punto inicial del dominio.
    initial_dot = domain.startswith(".")
    if (include_subdomains == "TRUE") != initial_dot:
        include_subdomains = "TRUE" if initial_dot else "FALSE"
    else:
        include_subdomains = "TRUE" if include_subdomains == "TRUE" else "FALSE"

    secure = "TRUE" if secure == "TRUE" else "FALSE"

    if expires:
        try:
            expires = str(int(float(expires)))
        except (TypeError, ValueError):
            return None

    return prefix + "\t".join(
        [domain, include_subdomains, cookie_path, secure, expires, name, value]
    )


def is_netscape_cookies(content: str) -> bool:
    """Comprueba si el contenido tiene al menos una cookie Netscape normalizable."""
    if not content or not content.strip():
        return False

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") and not stripped.startswith("#HttpOnly_"):
            continue
        if _normalize_cookie_line(stripped, filter_domains=False):
            return True

    return False


def sanitize_netscape_cookies(content: str) -> tuple[str, int]:
    """Devuelve un cookies.txt valido para http.cookiejar.

    Incluye la cabecera obligatoria, normaliza los flags, filtra dominios que
    no son de YouTube/Google y cuenta las lineas descartadas.
    """
    lines = ["# Netscape HTTP Cookie File"]
    dropped = 0

    if content:
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") and not stripped.startswith("#HttpOnly_"):
                continue
            normalized = _normalize_cookie_line(stripped, filter_domains=True)
            if normalized:
                lines.append(normalized)
            else:
                dropped += 1

    return "\n".join(lines) + "\n", dropped


def fix_netscape_cookies(content: str) -> str:
    """Compatibilidad: devuelve el contenido normalizado listo para yt-dlp."""
    return sanitize_netscape_cookies(content)[0]


def _write_temp_cookies(content: str) -> str:
    """Escribe las cookies en un archivo temporal privado (0600)."""
    fd, path = tempfile.mkstemp(prefix="ytdl-cookies-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    _TEMP_COOKIE_FILES.append(path)
    return path


def _load_from_content(content: str, source: str) -> bool:
    """Sanea, valida y registra el contenido de cookies indicado."""
    global COOKIES_PATH, COOKIES_VALID, COOKIES_ERROR, COOKIES_SOURCE
    global _COOKIES_CONTENT_SANITIZED

    sanitized, dropped = sanitize_netscape_cookies(content)
    if is_netscape_cookies(sanitized):
        _COOKIES_CONTENT_SANITIZED = sanitized
        COOKIES_PATH = _write_temp_cookies(sanitized)
        COOKIES_VALID = True
        COOKIES_SOURCE = source
        if dropped:
            COOKIES_ERROR = (
                f"Se ignoraron {dropped} linea(s) de cookies invalidas o de "
                "dominios ajenos a YouTube/Google."
            )
        return True

    _COOKIES_CONTENT_SANITIZED = ""
    COOKIES_ERROR = (
        "No se encontraron cookies validas de YouTube/Google. Verifica que el "
        "archivo sea un cookies.txt en formato Netscape y que hayas iniciado "
        "sesion en YouTube. Exportalo de nuevo con 'Get cookies.txt LOCALLY'."
    )
    return False


_BROWSER_SPEC_RE = re.compile(
    r"""
    ^(?P<name>[^+:]+)
    (?:\s*\+\s*(?P<keyring>[^:]+))?
    (?:\s*:\s*(?!:)(?P<profile>.+?))?
    (?:\s*::\s*(?P<container>.+))?
    $
    """,
    re.VERBOSE,
)


def parse_browser_spec(value: str) -> tuple[str, str | None, str | None, str | None]:
    """Convierte 'chrome:perfil::contenedor' en la tupla que espera yt-dlp."""
    match = _BROWSER_SPEC_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(
            f"Especificacion de navegador invalida: {value!r}. "
            "Usa, por ejemplo, 'chrome', 'firefox:default' o "
            "'chrome+keyring:perfil::contenedor'."
        )
    return (
        match.group("name").lower(),
        match.group("profile"),
        match.group("keyring"),
        match.group("container"),
    )


def load_cookie_config() -> None:
    """Carga la configuracion de cookies desde las variables de entorno."""
    global COOKIES_PATH, COOKIES_VALID, COOKIES_ERROR, COOKIES_SOURCE
    global COOKIES_FROM_BROWSER_SPEC, _COOKIES_CONTENT_SANITIZED

    COOKIES_PATH = None
    COOKIES_VALID = False
    COOKIES_ERROR = ""
    COOKIES_SOURCE = "none"
    COOKIES_FROM_BROWSER_SPEC = None
    _COOKIES_CONTENT_SANITIZED = ""

    if COOKIES_CONTENT:
        _load_from_content(COOKIES_CONTENT, "YTDLP_COOKIES")
    elif COOKIES_FILE:
        if not os.path.isfile(COOKIES_FILE):
            COOKIES_ERROR = (
                "El archivo de cookies configurado no existe: "
                f"{os.path.basename(COOKIES_FILE)}"
            )
        else:
            try:
                with open(COOKIES_FILE, "r", encoding="utf-8", errors="replace") as f:
                    file_content = f.read()
            except OSError as exc:
                COOKIES_ERROR = (
                    "No se pudo leer el archivo de cookies: "
                    f"{exc.strerror or 'error de lectura'}"
                )
            else:
                _load_from_content(file_content, "YTDLP_COOKIES_FILE")
    elif COOKIES_FROM_BROWSER:
        try:
            COOKIES_FROM_BROWSER_SPEC = parse_browser_spec(COOKIES_FROM_BROWSER)
        except ValueError as exc:
            COOKIES_ERROR = str(exc)
        else:
            COOKIES_VALID = True
            COOKIES_SOURCE = f"YTDLP_COOKIES_FROM_BROWSER ({COOKIES_FROM_BROWSER})"


load_cookie_config()


def ydl_opts_with_cookies(extra: dict) -> dict:
    """Agrega cookies a las opciones de yt-dlp si estan disponibles.

    yt-dlp reescribe el ``cookiefile`` al cerrar la instancia. Compartir un
    unico archivo entre peticiones concurrentes permitiria que una instancia
    lo trunque mientras otra lo esta leyendo, asi que se entrega una copia en
    memoria independiente por cada instancia de ``YoutubeDL``.
    """
    if _COOKIES_CONTENT_SANITIZED:
        extra["cookiefile"] = io.StringIO(_COOKIES_CONTENT_SANITIZED)
    elif COOKIES_PATH:
        extra["cookiefile"] = COOKIES_PATH
    if COOKIES_FROM_BROWSER_SPEC:
        extra["cookiesfrombrowser"] = COOKIES_FROM_BROWSER_SPEC
    return extra


def cookies_status() -> dict:
    """Devuelve un resumen de diagnostico sin exponer el contenido ni el origen

    de las cookies.
    """
    cookiefile_exists = False
    cookiefile_readable = False
    cookiefile_size = 0

    if COOKIES_PATH and os.path.exists(COOKIES_PATH):
        cookiefile_exists = True
        try:
            cookiefile_size = os.path.getsize(COOKIES_PATH)
            with open(COOKIES_PATH, "r", encoding="utf-8", errors="replace") as f:
                f.read(1)
            cookiefile_readable = True
        except OSError:
            cookiefile_readable = False

    configured = COOKIES_PATH is not None or COOKIES_FROM_BROWSER_SPEC is not None
    return {
        "cookies_configured": configured,
        "cookies_valid": COOKIES_VALID,
        "cookiefile_exists": cookiefile_exists,
        "cookiefile_readable": cookiefile_readable,
        "cookiefile_size": cookiefile_size,
        "cookies_error": COOKIES_ERROR if not COOKIES_VALID else "",
    }
