# Script PowerShell para reconstruir y reiniciar el backend con los nuevos cambios

Write-Host "==========================================" -ForegroundColor Blue
Write-Host "Reconstruyendo Backend Docker" -ForegroundColor Blue
Write-Host "==========================================" -ForegroundColor Blue
Write-Host ""

# Detener el contenedor backend
Write-Host "1. Deteniendo contenedor backend..." -ForegroundColor Yellow
docker-compose stop backend

# Reconstruir la imagen del backend (sin cache para asegurar cambios)
Write-Host "2. Reconstruyendo imagen del backend..." -ForegroundColor Yellow
docker-compose build --no-cache backend

# Aplicar migraciones
Write-Host "3. Aplicando migraciones..." -ForegroundColor Yellow
docker-compose run --rm backend python backend/manage.py migrate

# Reiniciar el contenedor
Write-Host "4. Reiniciando contenedor backend..." -ForegroundColor Yellow
docker-compose up -d backend

# Mostrar logs
Write-Host "5. Mostrando logs del backend (Ctrl+C para salir)..." -ForegroundColor Yellow
docker-compose logs -f backend
