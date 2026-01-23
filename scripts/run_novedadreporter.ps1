# Script PowerShell para ejecutar el bot de novedades
# Uso: .\scripts\run_novedadreporter.ps1 -UserEmail "email@ejemplo.com" [-Headless]
#   o: .\scripts\run_novedadreporter.ps1 -UserId 2 [-Headless]
#   o: .\scripts\run_novedadreporter.ps1 -Email "dropi@email.com" -Password "password" [-Headless]

param(
    [Parameter(Mandatory=$false)]
    [string]$UserEmail,
    
    [Parameter(Mandatory=$false)]
    [int]$UserId,
    
    [Parameter(Mandatory=$false)]
    [string]$Email,
    
    [Parameter(Mandatory=$false)]
    [string]$Password,
    
    [Parameter(Mandatory=$false)]
    [switch]$Headless
)

Write-Host "========================================" -ForegroundColor Blue
Write-Host "Ejecutando Bot de Novedades" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Validar que se proporcionó al menos una opción
if (-not $UserEmail -and -not $UserId -and (-not $Email -or -not $Password)) {
    Write-Host "ERROR: Debes proporcionar --UserEmail, --UserId, o --Email/--Password" -ForegroundColor Red
    Write-Host ""
    Write-Host "Ejemplos:" -ForegroundColor Yellow
    Write-Host "  .\scripts\run_novedadreporter.ps1 -UserEmail `"cliente@ejemplo.com`"" -ForegroundColor Yellow
    Write-Host "  .\scripts\run_novedadreporter.ps1 -UserId 2" -ForegroundColor Yellow
    Write-Host "  .\scripts\run_novedadreporter.ps1 -Email `"dropi@email.com`" -Password `"password`"" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "Modo headless: $(if ($Headless) { 'Sí' } else { 'No (visible)' })" -ForegroundColor Green
Write-Host ""

# Cambiar al directorio backend
$backendDir = Join-Path $PSScriptRoot "..\backend"
Set-Location $backendDir

# Construir comando
$command = "python manage.py novedadreporter"

if ($UserEmail) {
    Write-Host "Usuario cliente: $UserEmail" -ForegroundColor Green
    # Necesitamos obtener el user_id desde el email
    # Por ahora, usaremos --email/--password si están disponibles
    Write-Host "NOTA: Usando email del usuario. Si tienes credenciales DropiAccount configuradas, se usarán automáticamente." -ForegroundColor Yellow
}

if ($UserId) {
    Write-Host "User ID: $UserId" -ForegroundColor Green
    $command += " --user-id $UserId"
}

if ($Email) {
    Write-Host "Email Dropi: $Email" -ForegroundColor Green
    $command += " --email `"$Email`""
}

if ($Password) {
    $command += " --password `"$Password`""
}

if ($Headless) {
    $command += " --headless"
}

Write-Host ""
Write-Host "Ejecutando novedadreporter..." -ForegroundColor Green
Write-Host "Comando: $command" -ForegroundColor Yellow
Write-Host ""

# Ejecutar el bot
Invoke-Expression $command

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Bot de novedades completado" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
