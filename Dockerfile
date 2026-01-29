## Dockerfile para el pipeline completo de Dropi
# 1) Construye un contenedor ligero basado en Python slim
# 2) Instala dependencias del proyecto (pip + apt)
# 3) Configura Chromium para Selenium
# 4) Copia el código y define un comando por defecto

# --- Etapa base de Python ---
FROM python:3.11-slim AS base

# Evitar buffers en logs
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia e instala dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Instalación de Chromium y WebDriver (Full App) ---
FROM base AS full_app

# Instalar Chromium y chromedriver para Selenium
# Y librerías gráficas necesarias para PyTorch/Pillow/OpenCV
# TAMBIÉN INSTALAMOS MICROSOFT EDGE para consistencia con local
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    chromium chromium-driver \
    libgl1 libglib2.0-0 \
    wget gnupg2 ca-certificates \
    && wget -q -O - https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg \
    && install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/ \
    && sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge-dev.list' \
    && rm microsoft.gpg \
    && apt-get update \
    && apt-get install -y microsoft-edge-stable \
    && rm -rf /var/lib/apt/lists/*

# Variables de entorno para Selenium
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER=/usr/bin/chromedriver \
    EDGE_BIN=/usr/bin/microsoft-edge

# Copiar todo el código del proyecto
COPY . .

# Definir comando por defecto
CMD ["python", "scripts/scraper.py"]

# Alias for backward compatibility
FROM full_app AS selenium
FROM full_app AS vectorizer
