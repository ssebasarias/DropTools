# Script para ejecutar el flujo unificado en modo visible (local)
# Permite ver todos los pasos que realiza el bot
# Requiere: venv activado o existir .\venv en la raíz del proyecto

param(
    [Parameter(Mandatory=$true)]
    [int]$UserId,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet('chrome', 'edge', 'brave', 'firefox')]
    [string]$Browser = 'edge',
    
    [Parameter(Mandatory=$false)]
    [string]$DownloadDir = $null
)

$projectRoot = Join-Path $PSScriptRoot ".."
$venvActivate = Join-Path $projectRoot "venv" "Scripts" "Activate.ps1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  EJECUTANDO FLUJO UNIFICADO (LOCAL)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Usuario ID: $UserId" -ForegroundColor Yellow
Write-Host "Navegador: $Browser" -ForegroundColor Yellow
Write-Host "Modo: VISIBLE (podrás ver el navegador)" -ForegroundColor Green
Write-Host ""

Set-Location $projectRoot

# Activar venv si existe y no está ya activado
if (-not $env:VIRTUAL_ENV -and (Test-Path $venvActivate)) {
    Write-Host "Activando entorno virtual..." -ForegroundColor Gray
    & $venvActivate
}
elseif (-not $env:VIRTUAL_ENV) {
    Write-Host "AVISO: No se encontró venv. Crea uno con: python -m venv venv" -ForegroundColor Yellow
    Write-Host "       Luego: .\venv\Scripts\Activate.ps1  y  pip install -r requirements.txt" -ForegroundColor Yellow
}

# Ir al backend
$backendDir = Join-Path $projectRoot "backend"
Set-Location $backendDir

# Ejecutar el comando
$cmd = "python manage.py unified_reporter --user-id $UserId --browser $Browser"

if ($DownloadDir) {
    $cmd += " --download-dir `"$DownloadDir`""
}

Write-Host "Ejecutando: $cmd" -ForegroundColor Gray
Write-Host ""

Invoke-Expression $cmd

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PROCESO FINALIZADO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
