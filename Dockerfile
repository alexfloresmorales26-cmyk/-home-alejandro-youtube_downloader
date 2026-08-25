# Dockerfile para ejecutar el descargador de YouTube
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Instalar dependencias del sistema (ffmpeg requerido para conversiones)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \ 
       ffmpeg \ 
       build-essential \ 
    && rm -rf /var/lib/apt/lists/*

# Copiar requisitos e instalar paquetes Python
COPY requirements.txt requirements-dev.txt ./
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt || true

# Copiar el código de la aplicación
COPY . .

# Puerto por defecto para la interfaz web
EXPOSE 8080

# Comportamiento por defecto:
# - Si se establece APP_MODE=flask, ejecuta gunicorn sobre app:app
# - En otro caso, ejecuta la interfaz de consola (main.py)
CMD ["sh", "-c", "if [ \"${APP_MODE}\" = \"flask\" ]; then exec gunicorn -b 0.0.0.0:8080 app:app; else exec python main.py; fi"]
