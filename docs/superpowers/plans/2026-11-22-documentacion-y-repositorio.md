# Documentación y Repositorio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir y actualizar la documentación (README.md) del proyecto youtube_downloader para que coincida con el código real, y subir los cambios al repositorio remoto.

**Architecture:** Se actualizará únicamente README.md (documentación) para corregir inconsistencias con el código real (dependencias, puertos, estructura, variables de entorno, endpoints API, flags CLI, despliegue) y luego se hará commit + push al remoto origin/main.

**Tech Stack:** Markdown, Python (referencia), Git.

**Spec:** Código real del repositorio (app.py, downloader.py, main.py, gui.py, index.py, requirements.txt, Dockerfile, render.yaml, vercel.json, Procfile, templates/index.html, static/).

## Global Constraints

- El README debe describir exactamente lo que hace el código actual, sin inventar funcionalidades.
- Dependencias listadas deben coincidir con requirements.txt (flask, yt-dlp, gunicorn, pywebview).
- Puerto por defecto de app.py: 5000 (variable PORT); Docker expone 8080.
- gui.py no usa pywebview: arranca un servidor HTTP local y abre el navegador del sistema.
- FFmpeg es opcional en runtime pero necesario para conversiones de audio y merge de video+audio.
- Idioma de la documentación: español.

## Review Focus

- Dependencias inexistentes o faltantes en requirements.txt vs README.
- Puerto inconsistente entre README (5000) y Docker (8080).
- Variables de entorno (PORT, APP_MODE) no documentadas.
- Endpoints de API (/api/info, /api/download) no documentados.
- Flags de CLI de main.py no documentados.
- Estructura de archivos incompleta (falta api/index.py, index.py, Procfile, render.yaml, vercel.json, runtime.txt, .github/).

---

### Task 1: Reescribir README.md con documentación correcta y completa

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: código real de todos los .py, requirements.txt, Dockerfile, render.yaml, vercel.json, Procfile, runtime.txt, .github/workflows/
- Produces: README.md actualizado y coherente con el código

- [ ] **Step 1: Reescribir README.md**

Corregir:
- Título y descripción corta.
- 3 formas de usar (GUI, Web, CLI) con comandos exactos.
- Sección de características (reales, sin exagerar).
- Estructura del proyecto completa (incluir api/, index.py, Procfile, render.yaml, vercel.yml, .github/, static/, templates/).
- Instalación paso a paso (venv, requirements, ffmpeg, tests).
- Uso del CLI (main.py) con todos los flags argparse documentados.
- Uso del modo web (app.py) y variables de entorno (PORT, APP_MODE).
- Endpoints de la API (/api/info POST, /api/download GET/POST) con ejemplos.
- Despliegue en Docker (puerto 8080, APP_MODE=flask).
- Despliegue en Render/Railway.
- Requisitos del sistema (ffmpeg opcional, necesario para conversiones).
- Solución de problemas.

**Verification:** El archivo README.md se lee sin errores y describe con precisión el comportamiento del código.

- [ ] **Step 2: Ejecutar tests para verificar que nada se rompió**

Run: `python -m unittest -v`
Expected: Todas las pruebas pasan (las pruebas no tocan README, pero verificamos el estado del repo).

- [ ] **Step 3: Commit y push al repositorio**

Run:
```bash
git add README.md
git commit -m "docs: corregir y actualizar documentación completa del README"
git push origin main
```
Expected: Commit exitoso y push a origin/main sin errores.

---

**Plan complete and saved to `docs/superpowers/plans/2026-11-22-documentacion-y-repositorio.md`.** Since no execution method was explicitly supplied, I'll proceed with native execution in this session. The task is documentation-only with low inter-task dependency (just README.md), so native execution is appropriate.