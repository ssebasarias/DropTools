# Script PowerShell para ejecutar el workflow_orchestrator con un usuario cliente por email
# Uso: .\scripts\run_workflow_for_client.ps1 -ClientEmail "email@ejemplo.com" [-Headless]

param(
    [Parameter(Mandatory=$true)]
    [string]$ClientEmail,
    
    [Parameter(Mandatory=$false)]
    [switch]$Headless
)

Write-Host "========================================" -ForegroundColor Blue
Write-Host "Ejecutando Workflow Orchestrator" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Usuario cliente: $ClientEmail" -ForegroundColor Green
Write-Host "Modo headless: $(if ($Headless) { 'Sí' } else { 'No (visible)' })" -ForegroundColor Green
Write-Host ""

# Cambiar al directorio backend
$backendDir = Join-Path $PSScriptRoot "..\backend"
Set-Location $backendDir

# Construir comando
$command = "python manage.py workflow_orchestrator --user-email `"$ClientEmail`""
if ($Headless) {
    $command += " --headless"
}

Write-Host "Ejecutando workflow_orchestrator..." -ForegroundColor Green
Write-Host "Comando: $command" -ForegroundColor Yellow
Write-Host ""

# Ejecutar el orquestador
Invoke-Expression $command

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Workflow completado" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
