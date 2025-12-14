# ============================================
# SCRIPT DE REINICIO DE PROCESOS DAHELL
# ============================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "REINICIANDO PROCESOS DAHELL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Detener todos los procesos Python
Write-Host "1. Deteniendo procesos Python existentes..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | ForEach-Object {
        Write-Host "   Deteniendo proceso Python (PID: $($_.Id))..." -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Host "   OK Procesos detenidos" -ForegroundColor Green
}
else {
    Write-Host "   No hay procesos Python activos" -ForegroundColor Gray
}
Write-Host ""

# 2. Verificar que el venv existe
Write-Host "2. Verificando entorno virtual..." -ForegroundColor Yellow
if (Test-Path ".\venv\Scripts\python.exe") {
    Write-Host "   OK Entorno virtual encontrado" -ForegroundColor Green
}
else {
    Write-Host "   ERROR: No se encontro el entorno virtual" -ForegroundColor Red
    Write-Host "   Ejecuta: python -m venv venv" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# 3. Verificar Docker
Write-Host "3. Verificando Docker..." -ForegroundColor Yellow
try {
    $dockerCheck = docker ps 2>&1
    Write-Host "   OK Docker esta corriendo" -ForegroundColor Green
}
catch {
    Write-Host "   Docker no esta corriendo" -ForegroundColor Yellow
}
Write-Host ""

# 4. Mostrar instrucciones
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "INSTRUCCIONES PARA EJECUTAR LOS 4 PROCESOS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Abre 4 terminales PowerShell y ejecuta en cada una:" -ForegroundColor White
Write-Host ""
Write-Host "Terminal 1 - SCRAPER:" -ForegroundColor Green
Write-Host "  .\venv\Scripts\python.exe backend/core/management/commands/scraper.py" -ForegroundColor Gray
Write-Host ""
Write-Host "Terminal 2 - LOADER:" -ForegroundColor Green
Write-Host "  .\venv\Scripts\python.exe backend/core/management/commands/loader.py" -ForegroundColor Gray
Write-Host ""
Write-Host "Terminal 3 - VECTORIZER:" -ForegroundColor Green
Write-Host "  .\venv\Scripts\python.exe backend/core/management/commands/vectorizer.py" -ForegroundColor Gray
Write-Host ""
Write-Host "Terminal 4 - CLUSTERIZER:" -ForegroundColor Green
Write-Host "  .\venv\Scripts\python.exe backend/core/management/commands/clusterizer.py" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TODAS LAS CORRECCIONES YA ESTAN APLICADAS" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
