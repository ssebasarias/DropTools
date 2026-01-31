# =============================================================================
# Dahell Intelligence - Construir imagen Docker
# =============================================================================
# Ejecutar desde la raíz del proyecto o desde scripts.
# Requiere: Docker Desktop abierto.
#
# Uso:
#   .\scripts\build_docker_image.ps1
#   .\scripts\build_docker_image.ps1 -Target vectorizer   # Solo si usas vectorizer con GPU
# =============================================================================

param(
    [string]$Target = "selenium",
    [string]$Tag = "dahell-backend:latest"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { Get-Location }
if (-not (Test-Path "$ProjectRoot\Dockerfile")) {
    $ProjectRoot = Get-Location
}
if (-not (Test-Path "$ProjectRoot\Dockerfile")) {
    Write-Host "No se encontró Dockerfile. Ejecuta desde la raíz del proyecto (Dahell)." -ForegroundColor Red
    exit 1
}

Set-Location $ProjectRoot
Write-Host "Construyendo imagen Docker: $Tag (target: $Target)" -ForegroundColor Cyan
Write-Host "Proyecto: $ProjectRoot" -ForegroundColor Gray
Write-Host ""

docker build -t $Tag --target $Target .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al construir la imagen. Revisa que Docker Desktop esté abierto." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Imagen creada: $Tag" -ForegroundColor Green
Write-Host "Para levantar los contenedores: docker compose up -d" -ForegroundColor Cyan
