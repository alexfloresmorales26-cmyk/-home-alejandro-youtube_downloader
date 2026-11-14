# Dockerfile para Render - Descargador de YouTube
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
WORKDIR /app

# Instalar ffmpeg y dependencias del sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar requisitos e instalar paquetes Python
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Puerto para Render
EXPOSE 8080

# Comando de inicio para Render (modo Flask con gunicorn)
CMD exec gunicorn -b 0.0.0.0:$PORT app:app
