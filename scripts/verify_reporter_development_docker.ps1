# Verifica el flujo Iniciar a Reportar en modo desarrollo con Docker + Celery
# Ejecutar desde la raiz del proyecto: .\scripts\verify_reporter_development_docker.ps1

$ErrorActionPreference = "Stop"
$projectRoot = Join-Path $PSScriptRoot ".."
Set-Location $projectRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VERIFICACION: Modo desarrollo (Docker + Celery)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Estado de contenedores
Write-Host "[1/5] Contenedores Docker..." -ForegroundColor Yellow
$ps = docker compose ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: docker compose ps fallo. Docker esta corriendo?" -ForegroundColor Red
    Write-Host $ps
    exit 1
}
$ps | Select-String -Pattern "backend|celery_worker|redis" | ForEach-Object { Write-Host "  $_" }
$backendUp = ($ps | Select-String "backend" | Select-String "Up").Count -gt 0
$workerUp = ($ps | Select-String "celery_worker" | Select-String "Up").Count -gt 0
if (-not $backendUp -or -not $workerUp) {
    Write-Host "  Levanta los servicios: docker compose up -d" -ForegroundColor Red
    exit 1
}
Write-Host "  OK Backend y Celery worker estan Up" -ForegroundColor Green
Write-Host ""

# 2. API de modo (GET /api/reporter/env/)
Write-Host "[2/5] Modo activo (GET /api/reporter/env/)..." -ForegroundColor Yellow
try {
    $envResp = Invoke-RestMethod -Uri "http://localhost:8000/api/reporter/env/" -Method Get -TimeoutSec 5
    $envName = $envResp.droptools_env
    if (-not $envName) { $envName = $envResp.dahell_env }
    Write-Host "  droptools_env: $envName" -ForegroundColor Gray
    Write-Host "  run_mode: $($envResp.run_mode)" -ForegroundColor Gray
    Write-Host "  message: $($envResp.message)" -ForegroundColor Gray
    if ($envResp.run_mode -eq "development_docker") {
        Write-Host "  OK Modo desarrollo (Docker) detectado" -ForegroundColor Green
    } else {
        Write-Host "  AVISO: run_mode es $($envResp.run_mode). Usa DROPTOOLS_ENV=development en override." -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ERROR: No se pudo conectar al backend (http://localhost:8000)" -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 3. Obtener token para usuario 2 (via Django shell para cargar ORM)
Write-Host "[3/5] Token de usuario 2..." -ForegroundColor Yellow
$tokenLine = 'from rest_framework.authtoken.models import Token; from core.models import User; u = User.objects.get(id=2); t, _ = Token.objects.get_or_create(user=u); print(t.key)'
$tokenOut = docker compose exec -T backend python backend/manage.py shell -c $tokenLine 2>&1
$token = ($tokenOut | ForEach-Object { $_.Trim() } | Where-Object { $_ -match '^[a-zA-Z0-9]{30,}$' } | Select-Object -Last 1)
if (-not $token) { $token = ($tokenOut -join " ").Trim() }
if ($token -match "ERROR|Exception|DoesNotExist" -or $token.Length -lt 20) {
    Write-Host "  ERROR: $token" -ForegroundColor Red
    exit 1
}
Write-Host "  Token obtenido (primeros 8 chars): $($token.Substring(0, [Math]::Min(8, $token.Length)))..." -ForegroundColor Gray
Write-Host "  OK" -ForegroundColor Green
Write-Host ""

# 4. POST /api/reporter/start/ (disparar el reporter via Celery)
Write-Host "[4/5] Disparando reporter (POST /api/reporter/start/)..." -ForegroundColor Yellow
$headers = @{
    "Authorization" = "Token $token"
    "Content-Type"  = "application/json"
}
try {
    $startResp = Invoke-RestMethod -Uri "http://localhost:8000/api/reporter/start/" -Method Post -Headers $headers -TimeoutSec 15
    Write-Host "  status: $($startResp.status)" -ForegroundColor Gray
    Write-Host "  environment: $($startResp.environment)" -ForegroundColor Gray
    if ($startResp.task_id) { Write-Host "  task_id: $($startResp.task_id)" -ForegroundColor Gray }
    if ($startResp.status -eq "enqueued") {
        Write-Host "  OK Tarea encolada en Celery. El worker la ejecutara en segundo plano." -ForegroundColor Green
    } else {
        Write-Host "  Respuesta: $($startResp | ConvertTo-Json -Compress)" -ForegroundColor Gray
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    $body = ""
    try { $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream()); $body = $reader.ReadToEnd() } catch {}
    Write-Host "  ERROR HTTP $statusCode" -ForegroundColor Red
    Write-Host "  $body" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 5. Instrucciones para ver logs del worker
Write-Host "[5/5] Siguiente paso: ver logs del worker" -ForegroundColor Yellow
Write-Host "  Ejecuta en otra terminal:" -ForegroundColor Gray
Write-Host '    docker compose logs -f celery_worker' -ForegroundColor White
Write-Host '  Deberias ver la tarea y el reporter ejecutandose (Chromium/Firefox, descarga, etc).' -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Verificacion completada" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
