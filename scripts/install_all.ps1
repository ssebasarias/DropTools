# =============================================================================
# Dahell Intelligence - Instalación completa
# =============================================================================
# Ejecutar desde la raíz del proyecto o desde scripts:
#   .\scripts\install_all.ps1
# O desde la raíz:
#   .\install_all.ps1   (si copias el script a la raíz)
# =============================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path "$ProjectRoot\backend\manage.py")) {
    Write-Host "No se encontró la raíz del proyecto (backend\manage.py). Ejecuta desde Dahell o desde scripts." -ForegroundColor Red
    exit 1
}

Set-Location $ProjectRoot
Write-Host "Proyecto: $ProjectRoot" -ForegroundColor Cyan

# 1. Carpetas
foreach ($dir in @("raw_data", "logs", "cache_huggingface", "results")) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "Creado: $dir" -ForegroundColor Green
    }
}

# 2. .env y .env.docker
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Creado .env desde .env.example. Edítalo con tus contraseñas." -ForegroundColor Yellow
}
if (-not (Test-Path ".env.docker")) {
    Copy-Item ".env.example" ".env.docker"
    (Get-Content ".env.docker") -replace "POSTGRES_HOST=localhost", "POSTGRES_HOST=db" -replace "POSTGRES_PORT=5433", "POSTGRES_PORT=5432" -replace "redis://localhost:6379", "redis://redis:6379" | Set-Content ".env.docker"
    Write-Host "Creado .env.docker. Edítalo con tus contraseñas." -ForegroundColor Yellow
}

# 3. Venv y pip
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Creando entorno virtual..." -ForegroundColor Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Si falla venv, prueba: py -3.11 -m venv venv" -ForegroundColor Yellow
    }
}
if (Test-Path "venv\Scripts\pip.exe") {
    Write-Host "Instalando dependencias Python..." -ForegroundColor Cyan
    & ".\venv\Scripts\pip.exe" install -r requirements.txt
} else {
    Write-Host "Pip no encontrado en venv. Instala manualmente: .\venv\Scripts\Activate.ps1 ; pip install -r requirements.txt" -ForegroundColor Yellow
}

# 4. Frontend
Write-Host "Instalando dependencias del frontend..." -ForegroundColor Cyan
Set-Location frontend
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "npm install falló. Ejecuta manualmente: cd frontend ; npm install" -ForegroundColor Yellow
}
Set-Location $ProjectRoot

# 5. Docker
Write-Host "Levantando Docker (db, redis, backend, celery, flower, frontend)..." -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Revisa que Docker Desktop esté abierto y vuelve a ejecutar: docker compose up -d --build" -ForegroundColor Yellow
    exit 1
}

# Esperar a que el backend esté listo
Write-Host "Esperando a que el backend arranque (30 s)..." -ForegroundColor Cyan
Start-Sleep -Seconds 30

# 6. Migraciones
Write-Host "Aplicando migraciones..." -ForegroundColor Cyan
docker compose exec -T backend python manage.py migrate
Write-Host ""
Write-Host "Instalación lista." -ForegroundColor Green
Write-Host "Crear superusuario (opcional): docker compose exec backend python manage.py createsuperuser" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Admin: http://localhost:8000/admin" -ForegroundColor Cyan
Write-Host "Flower: http://localhost:5555" -ForegroundColor Cyan
Write-Host "pgAdmin: http://localhost:5050" -ForegroundColor Cyan
