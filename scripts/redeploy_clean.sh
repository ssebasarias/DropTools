#!/bin/bash

# ==============================================================================
# SCRIPT DE REINICIO TOTAL PARA PRODUCCIÓN
# ==============================================================================
# Este script realiza un despliegue limpio:
# 1. Descarga el código más reciente.
# 2. Destruye la base de datos actual (para corregir errores de consistencia).
# 3. Reconstruye los contenedores.
# 4. Inicia todo desde cero, permitiendo que Django cree la estructura de DB correcta.
# ==============================================================================

# Detener el script si hay errores
set -e

echo "========================================================"
echo "⚠️  PELIGRO: REINICIO TOTAL DE BASE DE DATOS ⚠️"
echo "========================================================"
echo "Este script eliminará permanentemente la base de datos actual."
echo "Se perderán todos los usuarios, órdenes y configuraciones."
echo "Úsalo solo si necesitas arreglar errores graves de migración."
echo "========================================================"
read -p "¿Estás SEGURO de continuar? (escribe 'si' para confirmar): " confirmation

if [ "$confirmation" != "si" ]; then
    echo "Cancelado."
    exit 1
fi

echo ""
echo "📥 1. Descargando últimos cambios de GitHub..."
git pull

echo ""
echo "🛑 2. Deteniendo contenedores y ELIMINANDO volúmenes de datos..."
# -v elimina los volúmenes (la base de datos)
docker compose -f docker-compose.production.yml down -v

echo ""
echo "🏗️  3. Reconstruyendo e iniciando servicios..."
# --build fuerza la recompilación del código
docker compose -f docker-compose.production.yml up -d --build

echo ""
echo "⏳ 4. Esperando a que el backend inicie y aplique migraciones..."
echo "      (Esto puede tardar unos segundos mientras la DB se inicializa)"
sleep 5

echo ""
echo "✅ ¡Listo! El sistema se ha reiniciado."
echo ""
echo "📜 Para ver el progreso de las migraciones en tiempo real:"
echo "   docker logs -f droptools_backend"
echo ""
echo "👤 Para crear tu usuario administrador (cuando terminen los logs):"
echo "   docker exec -it droptools_backend python backend/manage.py createsuperuser"
