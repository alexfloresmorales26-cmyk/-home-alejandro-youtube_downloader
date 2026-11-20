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
