#!/bin/bash
# ============================================================================
# GUÍA DE DEPLOYMENT - Dahell Intelligence en VPS Linux
# ============================================================================
# Este script te guía paso a paso en el deployment inicial del proyecto

set -e  # Salir si hay error

echo "=========================================="
echo "DAHELL INTELLIGENCE - DEPLOYMENT GUIDE"
echo "=========================================="
echo ""

# ========================================
# PASO 1: Verificar prerequisitos
# ========================================
echo "PASO 1: Verificando prerequisitos..."
echo ""

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado"
    echo "   Instalar con: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    exit 1
else
    echo "✅ Docker instalado: $(docker --version)"
fi

# Verificar Docker Compose
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose no está instalado"
    echo "   Instalar con: sudo apt install docker-compose-plugin -y"
    exit 1
else
    echo "✅ Docker Compose instalado"
fi

# Verificar Git
if ! command -v git &> /dev/null; then
    echo "❌ Git no está instalado"
    echo "   Instalar con: sudo apt install git -y"
    exit 1
else
    echo "✅ Git instalado: $(git --version)"
fi

echo ""
echo "=========================================="

# ========================================
# PASO 2: Configurar variables de entorno
# ========================================
echo "PASO 2: Configurando variables de entorno..."
echo ""

if [ ! -f .env.production ]; then
    echo "⚠️  Archivo .env.production no encontrado"
    echo "   Creando desde plantilla .env.docker..."
    cp .env.docker .env.production
    echo ""
    echo "⚠️  IMPORTANTE: Edita .env.production y cambia:"
    echo "   - DEBUG=False"
    echo "   - SECRET_KEY (genera una nueva)"
    echo "   - POSTGRES_PASSWORD (contraseña segura)"
    echo "   - PGADMIN_DEFAULT_PASSWORD (contraseña segura)"
    echo "   - ALLOWED_HOSTS (tu dominio/IP)"
    echo ""
    read -p "Presiona ENTER cuando hayas editado .env.production..."
else
    echo "✅ Archivo .env.production encontrado"
fi

echo ""
echo "=========================================="

# ========================================
# PASO 3: Crear directorios necesarios
# ========================================
echo "PASO 3: Creando directorios necesarios..."
echo ""

mkdir -p logs
mkdir -p raw_data
mkdir -p backups
mkdir -p cache_huggingface
mkdir -p nginx/ssl

echo "✅ Directorios creados"
echo ""
echo "=========================================="

# ========================================
# PASO 4: Configurar SSL (Opcional)
# ========================================
echo "PASO 4: Configurar SSL..."
echo ""

if [ ! -f nginx/ssl/cert.pem ]; then
    echo "⚠️  Certificado SSL no encontrado"
    echo ""
    echo "Opciones:"
    echo "1. Generar certificado autofirmado (para pruebas)"
    echo "2. Usar Let's Encrypt (para producción)"
    echo "3. Omitir (configurar después)"
    echo ""
    read -p "Selecciona una opción (1/2/3): " ssl_option
    
    case $ssl_option in
        1)
            echo "Generando certificado autofirmado..."
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                -keyout nginx/ssl/key.pem \
                -out nginx/ssl/cert.pem \
                -subj "/C=CO/ST=Bogota/L=Bogota/O=Dahell/CN=localhost"
            echo "✅ Certificado autofirmado generado"
            ;;
        2)
            echo "Para Let's Encrypt, ejecuta después del deployment:"
            echo "   sudo certbot --nginx -d tu-dominio.com"
            ;;
        3)
            echo "⚠️  SSL omitido. Configura después."
            ;;
    esac
else
    echo "✅ Certificado SSL encontrado"
fi

echo ""
echo "=========================================="

# ========================================
# PASO 5: Construir imágenes Docker
# ========================================
echo "PASO 5: Construyendo imágenes Docker..."
echo ""

read -p "¿Construir imágenes ahora? (s/n): " build_images

if [ "$build_images" = "s" ]; then
    echo "Construyendo imágenes (esto puede tardar 10-15 minutos)..."
    docker compose -f docker-compose.production.yml --env-file .env.production build
    echo "✅ Imágenes construidas"
else
    echo "⚠️  Construcción omitida. Ejecuta manualmente:"
    echo "   docker compose -f docker-compose.production.yml --env-file .env.production build"
fi

echo ""
echo "=========================================="

# ========================================
# PASO 6: Iniciar servicios base
# ========================================
echo "PASO 6: Iniciando servicios base..."
echo ""

read -p "¿Iniciar servicios base (db, backend, frontend)? (s/n): " start_services

if [ "$start_services" = "s" ]; then
    echo "Iniciando servicios..."
    docker compose -f docker-compose.production.yml --env-file .env.production up -d db backend frontend nginx portainer
    
    echo ""
    echo "Esperando a que la base de datos esté lista..."
    sleep 10
    
    echo "✅ Servicios iniciados"
    echo ""
    echo "Servicios disponibles:"
    echo "   - Frontend: http://localhost (o https://tu-dominio.com)"
    echo "   - Backend API: http://localhost/api/"
    echo "   - Django Admin: http://localhost/admin/"
    echo "   - Portainer: http://localhost:9000"
else
    echo "⚠️  Inicio omitido. Ejecuta manualmente:"
    echo "   docker compose -f docker-compose.production.yml --env-file .env.production up -d"
fi

echo ""
echo "=========================================="

# ========================================
# PASO 7: Configurar cron jobs
# ========================================
echo "PASO 7: Configurar tareas programadas (cron)..."
echo ""

echo "Tareas recomendadas:"
echo ""
echo "# Backup diario de base de datos (3:00 AM)"
echo "0 3 * * * /opt/Dahell/scripts/backup_db.sh >> /var/log/dahell_backup.log 2>&1"
echo ""
echo "# Limpieza semanal de datos (Domingos 2:00 AM)"
echo "0 2 * * 0 /opt/Dahell/scripts/cleanup_old_data.sh >> /var/log/dahell_cleanup.log 2>&1"
echo ""
echo "# Limpieza mensual de base de datos (Primer día del mes 4:00 AM)"
echo "0 4 1 * * docker exec dahell_db psql -U dahell_admin -d dahell_db -f /app/scripts/cleanup_db.sql >> /var/log/dahell_db_cleanup.log 2>&1"
echo ""

read -p "¿Agregar estas tareas a crontab? (s/n): " add_cron

if [ "$add_cron" = "s" ]; then
    (crontab -l 2>/dev/null; echo "# Dahell Intelligence - Automated Tasks") | crontab -
    (crontab -l 2>/dev/null; echo "0 3 * * * /opt/Dahell/scripts/backup_db.sh >> /var/log/dahell_backup.log 2>&1") | crontab -
    (crontab -l 2>/dev/null; echo "0 2 * * 0 /opt/Dahell/scripts/cleanup_old_data.sh >> /var/log/dahell_cleanup.log 2>&1") | crontab -
    (crontab -l 2>/dev/null; echo "0 4 1 * * docker exec dahell_db psql -U dahell_admin -d dahell_db -f /app/scripts/cleanup_db.sql >> /var/log/dahell_db_cleanup.log 2>&1") | crontab -
    echo "✅ Tareas agregadas a crontab"
else
    echo "⚠️  Cron omitido. Agrega manualmente con: crontab -e"
fi

echo ""
echo "=========================================="

# ========================================
# PASO 8: Dar permisos a scripts
# ========================================
echo "PASO 8: Configurando permisos de scripts..."
echo ""

chmod +x scripts/*.sh
echo "✅ Permisos configurados"

echo ""
echo "=========================================="

# ========================================
# RESUMEN FINAL
# ========================================
echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETADO"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo ""
echo "1. Verificar que los servicios estén corriendo:"
echo "   docker ps"
echo ""
echo "2. Ver logs de servicios:"
echo "   docker compose -f docker-compose.production.yml logs -f"
echo ""
echo "3. Iniciar workers (uno por uno):"
echo "   docker compose -f docker-compose.production.yml --profile workers up -d scraper"
echo "   docker compose -f docker-compose.production.yml --profile workers up -d loader"
echo "   docker compose -f docker-compose.production.yml --profile workers up -d vectorizer"
echo ""
echo "4. Monitorear recursos:"
echo "   docker stats"
echo "   htop"
echo ""
echo "5. Configurar firewall (UFW):"
echo "   sudo ufw allow 22/tcp"
echo "   sudo ufw allow 80/tcp"
echo "   sudo ufw allow 443/tcp"
echo "   sudo ufw enable"
echo ""
echo "=========================================="
echo "Para más información, consulta: ANALISIS_DEPLOYMENT_VPS.md"
echo "=========================================="
