#!/bin/bash
# ============================================================================
# BACKUP AUTOMÁTICO DE BASE DE DATOS - Dahell Intelligence
# ============================================================================
# Uso: ./backup_db.sh
# Cron: 0 3 * * * /opt/Dahell/scripts/backup_db.sh >> /var/log/dahell_backup.log 2>&1

set -e  # Salir si hay error

# Configuración
BACKUP_DIR="/opt/Dahell/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/dahell_db_$TIMESTAMP.sql.gz"
RETENTION_DAYS=7  # Mantener backups de los últimos 7 días

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

echo "=========================================="
echo "Iniciando backup de base de datos"
echo "Fecha: $(date)"
echo "=========================================="

# Realizar backup comprimido
echo "Creando backup..."
docker exec dahell_db pg_dump -U dahell_admin dahell_db | gzip > "$BACKUP_FILE"

# Verificar que el backup se creó correctamente
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup completado exitosamente"
    echo "   Archivo: $BACKUP_FILE"
    echo "   Tamaño: $BACKUP_SIZE"
else
    echo "❌ ERROR: El backup no se creó correctamente"
    exit 1
fi

# Eliminar backups antiguos
echo "Eliminando backups antiguos (más de $RETENTION_DAYS días)..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "dahell_db_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
echo "   Backups eliminados: $DELETED_COUNT"

# Listar backups disponibles
echo "=========================================="
echo "Backups disponibles:"
ls -lh "$BACKUP_DIR"/dahell_db_*.sql.gz 2>/dev/null || echo "   No hay backups disponibles"
echo "=========================================="

# Estadísticas de espacio
TOTAL_BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "Espacio total usado por backups: $TOTAL_BACKUP_SIZE"

echo "Backup completado: $(date)"
