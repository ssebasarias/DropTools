# Inicia Backend (Django) en puerto 8000
# Ejecutar desde la raiz: .\scripts\iniciar_desarrollo.ps1
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location (Join-Path $root "backend")
Write-Host "Iniciando Backend Django en http://localhost:8000 ..." -ForegroundColor Green
python manage.py runserver 0.0.0.0:8000
