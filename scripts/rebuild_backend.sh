#!/bin/bash
# Script para reconstruir y reiniciar el backend con los nuevos cambios

echo "=========================================="
echo "Reconstruyendo Backend Docker"
echo "=========================================="

# Detener el contenedor backend
echo "1. Deteniendo contenedor backend..."
docker-compose stop backend

# Reconstruir la imagen del backend (sin cache para asegurar cambios)
echo "2. Reconstruyendo imagen del backend..."
docker-compose build --no-cache backend

# Aplicar migraciones
echo "3. Aplicando migraciones..."
docker-compose run --rm backend python backend/manage.py migrate

# Reiniciar el contenedor
echo "4. Reiniciando contenedor backend..."
docker-compose up -d backend

# Mostrar logs
echo "5. Mostrando logs del backend..."
docker-compose logs -f backend
