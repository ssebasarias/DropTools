# Script para ejecutar el flujo unificado en modo visible (local)
# Permite ver todos los pasos que realiza el bot

param(
    [Parameter(Mandatory=$true)]
    [int]$UserId,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet('chrome', 'edge', 'brave', 'firefox')]
    [string]$Browser = 'edge',
    
    [Parameter(Mandatory=$false)]
    [string]$DownloadDir = $null
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  EJECUTANDO FLUJO UNIFICADO (LOCAL)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Usuario ID: $UserId" -ForegroundColor Yellow
Write-Host "Navegador: $Browser" -ForegroundColor Yellow
Write-Host "Modo: VISIBLE (podrás ver el navegador)" -ForegroundColor Green
Write-Host ""

# Cambiar al directorio del backend
$backendDir = Join-Path $PSScriptRoot ".." "backend"
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
