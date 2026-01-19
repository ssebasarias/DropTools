#!/bin/bash
# ============================================================================
# LIMPIEZA AUTOMÁTICA DE DATOS ANTIGUOS - Dahell Intelligence
# ============================================================================
# Uso: ./cleanup_old_data.sh
# Cron: 0 2 * * 0 /opt/Dahell/scripts/cleanup_old_data.sh >> /var/log/dahell_cleanup.log 2>&1

set -e  # Salir si hay error

echo "=========================================="
echo "Iniciando limpieza de datos antiguos"
echo "Fecha: $(date)"
echo "=========================================="

# Directorio del proyecto
PROJECT_DIR="/opt/Dahell"

# ========================================
# 1. Limpiar logs antiguos (más de 30 días)
# ========================================
echo "1. Limpiando logs antiguos (>30 días)..."
LOGS_DELETED=$(find "$PROJECT_DIR/logs" -name "*.log" -mtime +30 -delete -print | wc -l)
echo "   Logs eliminados: $LOGS_DELETED"

# ========================================
# 2. Comprimir logs recientes (7-30 días)
# ========================================
echo "2. Comprimiendo logs recientes (7-30 días)..."
LOGS_COMPRESSED=0
for log_file in $(find "$PROJECT_DIR/logs" -name "*.log" -mtime +7 -mtime -30); do
    if [ -f "$log_file" ]; then
        gzip "$log_file"
        LOGS_COMPRESSED=$((LOGS_COMPRESSED + 1))
    fi
done
echo "   Logs comprimidos: $LOGS_COMPRESSED"

# ========================================
# 3. Limpiar datos crudos procesados (más de 60 días)
# ========================================
echo "3. Limpiando datos crudos antiguos (>60 días)..."
RAW_DELETED=$(find "$PROJECT_DIR/raw_data" -name "*.jsonl" -mtime +60 -delete -print | wc -l)
echo "   Archivos JSONL eliminados: $RAW_DELETED"

# ========================================
# 4. Limpiar archivos tar.gz antiguos (más de 90 días)
# ========================================
echo "4. Limpiando archivos comprimidos antiguos (>90 días)..."
TAR_DELETED=$(find "$PROJECT_DIR/raw_data" -name "*.tar.gz" -mtime +90 -delete -print | wc -l)
echo "   Archivos TAR.GZ eliminados: $TAR_DELETED"

# ========================================
# 5. Limpiar cache de Docker (imágenes sin usar)
# ========================================
echo "5. Limpiando cache de Docker..."
docker system prune -f --volumes > /dev/null 2>&1
echo "   Cache de Docker limpiado"

# ========================================
# 6. Estadísticas de espacio
# ========================================
echo "=========================================="
echo "Estadísticas de espacio en disco:"
echo "=========================================="
df -h "$PROJECT_DIR" | tail -n 1

echo ""
echo "Uso de espacio por directorio:"
du -sh "$PROJECT_DIR/logs" 2>/dev/null || echo "   logs: 0 MB"
du -sh "$PROJECT_DIR/raw_data" 2>/dev/null || echo "   raw_data: 0 MB"
du -sh "$PROJECT_DIR/backups" 2>/dev/null || echo "   backups: 0 MB"
du -sh "$PROJECT_DIR/cache_huggingface" 2>/dev/null || echo "   cache_huggingface: 0 MB"

echo "=========================================="
echo "Limpieza completada: $(date)"
echo "=========================================="
