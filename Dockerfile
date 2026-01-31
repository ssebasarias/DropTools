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

# Instalar solo Chromium y Firefox para Selenium (Linux): estables y compatibles
# Edge no se instala en Linux (inestable/msedgedriver); en local Windows sí se puede usar
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    chromium chromium-driver \
    firefox-esr \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Variables de entorno para Selenium (Linux)
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER=/usr/bin/chromedriver

# Copiar todo el código del proyecto
COPY . .

# Definir comando por defecto
CMD ["python", "scripts/scraper.py"]

# Alias for backward compatibility
FROM full_app AS selenium
FROM full_app AS vectorizer
