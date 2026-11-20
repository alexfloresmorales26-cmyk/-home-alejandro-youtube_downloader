Acciones aplicadas por el asistente (registro)

## 2026-11-19 - Corrección de errores críticos

- Se corrigió `validate_youtube_url()` en `app.py`: devolvía `(False,)` y provocaba
  `ValueError: not enough values to unpack` con URLs inválidas.
- Se centralizó la validación de URLs en `utils.py` (acepta `youtube.com`,
  `m.youtube.com`, `music.youtube.com`, `youtu.be`, shorts, directos y playlists).
- Se centralizó la carga de cookies en `cookies.py`:
  - Detecta correctamente archivos Netscape separados por tabuladores.
  - Soporta líneas `#HttpOnly_`.
  - Repara copias con espacios sin modificar el archivo original.
  - Carga `.env` automáticamente y resuelve rutas relativas contra la raíz.
  - Convierte `YTDLP_COOKIES_FROM_BROWSER` a la tupla que espera yt-dlp.
- Se corrigió el preflight `HEAD /api/download`: ya no descarga el video dos veces
  en Flask y funciona en el servidor nativo del modo escritorio.
- Se añadió `core.py` con la lógica compartida de metadatos/descargas para evitar
  que `app.py` y `api/index.py` se desincronicen.
- Las descargas se envían desde disco (streaming) en lugar de cargar el archivo
  completo en memoria; si hay varios archivos (playlist) se entrega un ZIP.
- La limpieza de temporales solo elimina directorios con prefijo `ytdl-`, sin
  tocar los `/tmp/tmp*` de otras aplicaciones.
- Se añadió `.dockerignore` para no incluir `.env`, `cookies.txt`, `.venv` ni
  descargas en la imagen Docker.
- Se actualizó el frontend: validación de URLs equivalente al backend, manejo de
  playlists, mensajes de error con saltos de línea y conservación de la calidad
  seleccionada al cambiar entre las pestañas de video y audio.
- Se añadió un favicon SVG embebido para evitar el error 404 de `/favicon.ico`.
- Se añadieron pruebas de regresión en `test_app.py` (23 pruebas en total).
- Se actualizó la documentación de cookies, estructura, Docker y solución de problemas.

- Se añadieron workflows de CI y autoformateo (.github/workflows/ci.yml, autoformat.yml, ci-automerge.yml, create-pr.yml, notify-on-merge.yml).
- Se añadió requirements-dev.txt y .pre-commit-config.yaml para linters y formateo.
- Se añadió .venv/ a .gitignore y se removió su seguimiento.
- Se mejoraron los workflows para ser más robustos y tolerantes a errores.
- Se corrigió send_file() en app.py y api/index.py para usar io.BytesIO con contenido de descarga.
- Se eliminó la función duplicada _ydl_opts_with_cookies() en downloader.py.
- Se agregó control de versiones v1.0.0 (archivo VERSION y __version__ en módulos).
- Se mostró la versión 1.0.0 en el pie de página de la interfaz web (templates/index.html).
- Se actualizó el árbol de archivos y comandos en README.md.

Fecha de acción: 2026-11-13

Nota: Las correcciones automáticas de formato serán aplicadas por el workflow Autoformat. Esas commits son realizados por github-actions[bot].

## 2026-11-19 - Segunda pasada de revisión

- `cookies.py`: se eliminó la condición de carrera del `cookiefile`. yt-dlp
  reescribe el archivo al cerrar la instancia, así que dos peticiones concurrentes
  podían truncarlo mientras otra lo leía. Ahora el contenido saneado se guarda en
  memoria y cada instancia de `YoutubeDL` recibe su propio `io.StringIO`.
- `cookies.py`: `cookies_status()` ya no expone rutas del sistema
  (`cookies_path`/`cookies_file`); devuelve `cookies_file_configured` y los errores
  usan solo el nombre base del archivo.
- `utils.py`: la limpieza de temporales no borra descargas activas (detecta
  archivos `.part`/`.ytdl` o archivos recientes aunque el directorio sea antiguo).
- `utils.py`: `list_downloaded_files()` ignora archivos de 0 bytes y `youtu.be`
  exige exactamente un segmento de ruta.
- `core.py`: se validan `type` y `quality` antes de construir el formato de yt-dlp
  (`DOWNLOAD_TYPES`, `AUDIO_FORMATS`, `VIDEO_QUALITY_RE`); una calidad inválida cae
  a `best` y una altura `0`/no numérica se descarta. La miniatura de playlist
  prefiere `info["thumbnail"]`.
- `downloader.py`: `_build_video_format()` rechaza alturas no numéricas o `0`;
  `get_available_resolutions()` es tolerante a `None`; `download_audio()` valida el
  formato recibido.
- `app.py` y `api/index.py`: un cuerpo JSON que no sea objeto devuelve 400 en vez
  de 500; `type`/`quality` se convierten a texto; el servidor nativo incorpora
  `GET /api/cookies-status`; las rutas estáticas usan `realpath` (symlinks) y un
  `PORT` inválido cae a 5000.
- Frontend: la duración se escribe en `#video-duration-value` para no borrar el
  icono; en playlists se oculta la insignia; una miniatura ausente no genera una
  petición inválida y un error de carga la oculta; el fallback de error solo repite
  la petición ante un 400.
- Despliegue: gunicorn usa `gthread` con `--timeout 600` para no matar descargas
  largas; `vercel.json` incluye los módulos compartidos y `templates/`/`static/`.
- Workflows: se define `TOKEN` en `autoformat.yml` y `create-pr.yml` (fallaban con
  401), los payloads JSON se construyen con `jq`, el autoformateo solo corre en
  `main`, `create-pr` omite ramas `autoformat/*` y el auto-merge solo fusiona PRs
  de `autoformat/*` con checks exitosos y estado `clean`/`has_hooks`.
- `main.py`: `show_video_details()` tolera `None`, el cambio de carpeta maneja
  `OSError`, `--format` usa `choices` y la CLI sale con código 1 si falla la
  descarga. `gui.py`: `server_close()` se ejecuta siempre en `finally`.
- README: comando de pruebas completo, eliminación de `APP_MODE` (no existía) y
  límites reales de Vercel (sin ffmpeg, ~4,5 MB de respuesta y tiempo de ejecución).
- Pruebas: 40 en total (`python -m unittest -v`), con cobertura nueva para
  normalización de opciones, aislamiento del flujo de cookies, ocultamiento de
  rutas, protección de descargas activas, archivos vacíos, JSON no-objeto,
  `cookies-status` nativo y segmentos extra en `youtu.be`.
