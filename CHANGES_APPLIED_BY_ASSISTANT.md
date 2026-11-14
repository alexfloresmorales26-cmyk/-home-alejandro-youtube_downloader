Acciones aplicadas por el asistente (registro)

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
