# Aplicar migraciones, reconstruir imágenes y reiniciar servicios Dahell
# Ejecutar desde la raíz del proyecto: .\scripts\apply_migrations_and_restart.ps1

$ErrorActionPreference = "Stop"
# Si ejecutas desde la raíz: .\scripts\apply_migrations_and_restart.ps1 → $PSScriptRoot = ...\scripts
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $ProjectRoot "docker-compose.yml"))) {
    $ProjectRoot = Get-Location
}
Set-Location $ProjectRoot

Write-Host "=== Proyecto: $ProjectRoot ===" -ForegroundColor Cyan

# 1. Bajar contenedores
Write-Host "`n1. Deteniendo contenedores..." -ForegroundColor Yellow
docker compose down

# 2. Reconstruir imágenes (sin caché para que se vean los cambios)
Write-Host "`n2. Reconstruyendo imágenes..." -ForegroundColor Yellow
docker compose build --no-cache

# 3. Levantar servicios
Write-Host "`n3. Levantando servicios..." -ForegroundColor Yellow
docker compose up -d

# 4. Esperar a que la DB y el backend estén listos
Write-Host "`n4. Esperando a que DB y backend estén listos (15 s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# 5. Ejecutar migraciones dentro del contenedor backend
Write-Host "`n5. Aplicando migraciones Django..." -ForegroundColor Yellow
docker compose exec -T backend python backend/manage.py migrate --noinput

Write-Host "`n=== Listo. Servicios en ejecución. ===" -ForegroundColor Green
Write-Host "Backend: http://localhost:8000" -ForegroundColor Gray
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Gray
Write-Host "Flower: http://localhost:5555" -ForegroundColor Gray
