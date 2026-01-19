#!/bin/bash
# ============================================================================
# SCRIPT DE ACTUALIZACIÓN - Dahell Intelligence
# ============================================================================
# Uso: ./update.sh
# Descripción: Obtiene cambios de GitHub y reinicia servicios

set -e  # Salir si hay error

cd /opt/Dahell

echo "=========================================="
echo "Actualizando Dahell Intelligence..."
echo "Fecha: $(date)"
echo "=========================================="

# 1. Obtener cambios de GitHub
echo ""
echo "1. Obteniendo cambios de GitHub..."
git fetch origin
BEFORE=$(git rev-parse HEAD)
git pull origin main
AFTER=$(git rev-parse HEAD)

if [ "$BEFORE" = "$AFTER" ]; then
    echo "   ✅ No hay cambios nuevos"
    echo "=========================================="
    exit 0
else
    echo "   ✅ Cambios detectados"
    git log --oneline $BEFORE..$AFTER
fi

# 2. Verificar si hay cambios en archivos críticos
echo ""
echo "2. Verificando archivos modificados..."
CHANGED_FILES=$(git diff --name-only $BEFORE $AFTER)
echo "$CHANGED_FILES"

# 3. Detener servicios
echo ""
echo "3. Deteniendo servicios..."
docker compose -f docker-compose.production.yml down

# 4. Reconstruir imágenes si es necesario
if echo "$CHANGED_FILES" | grep -q "requirements.txt\|Dockerfile"; then
    echo ""
    echo "4. Detectados cambios en dependencias, reconstruyendo imágenes..."
    docker compose -f docker-compose.production.yml build --no-cache
else
    echo ""
    echo "4. No se detectaron cambios en dependencias, usando imágenes existentes..."
fi

# 5. Iniciar servicios
echo ""
echo "5. Iniciando servicios..."
docker compose -f docker-compose.production.yml up -d

# 6. Esperar a que los servicios estén listos
echo ""
echo "6. Esperando a que los servicios estén listos..."
sleep 10

# 7. Verificar estado
echo ""
echo "7. Verificando estado de servicios..."
docker ps --filter "name=dahell_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 8. Mostrar logs recientes
echo ""
echo "8. Logs recientes (últimas 20 líneas)..."
docker compose -f docker-compose.production.yml logs --tail=20

echo ""
echo "=========================================="
echo "✅ Actualización completada: $(date)"
echo "=========================================="
echo ""
echo "Servicios disponibles:"
echo "   - Frontend: https://tu-dominio.com"
echo "   - Backend API: https://tu-dominio.com/api/"
echo "   - Django Admin: https://tu-dominio.com/admin/"
echo ""
echo "Para ver logs en tiempo real:"
echo "   docker compose -f docker-compose.production.yml logs -f"
echo ""
