# ============================================================================
# SCRIPT DE SINCRONIZACIÓN - Dahell Intelligence
# ============================================================================
# Uso: .\sync_to_server.ps1
# Uso con dry-run: .\sync_to_server.ps1 -DryRun

param(
    [switch]$DryRun = $false,  # Usar -DryRun para ver qué se sincronizaría
    [switch]$Restart = $false  # Usar -Restart para reiniciar servicios después
)

# ========================================
# CONFIGURACIÓN (⚠️ CAMBIAR ESTOS VALORES)
# ========================================
$LocalPath = "C:\Users\guerr\Documents\AnalisisDeDatos\Dahell\"
$RemoteUser = "usuario"  # ⚠️ CAMBIAR por tu usuario SSH
$RemoteHost = "ip-del-vps"  # ⚠️ CAMBIAR por la IP de tu VPS
$RemotePath = "/opt/Dahell/"

Write-Host "=========================================="
Write-Host "Sincronizando Dahell Intelligence..."
Write-Host "=========================================="
Write-Host ""
Write-Host "Origen:  $LocalPath"
Write-Host "Destino: ${RemoteUser}@${RemoteHost}:${RemotePath}"
Write-Host ""

# ========================================
# OPCIONES DE RSYNC
# ========================================
$RsyncOptions = @(
    "-avz",                    # Archive, verbose, compress
    "--progress",              # Mostrar progreso
    "--delete",                # Eliminar archivos que ya no existen en origen
    "--exclude='.git/'",       # Excluir .git
    "--exclude='venv/'",       # Excluir entorno virtual
    "--exclude='__pycache__/'", # Excluir cache de Python
    "--exclude='*.pyc'",       # Excluir archivos compilados
    "--exclude='.env'",        # Excluir .env local
    "--exclude='logs/'",       # Excluir logs (se generan en servidor)
    "--exclude='raw_data/'",   # Excluir datos crudos (se generan en servidor)
    "--exclude='backups/'",    # Excluir backups
    "--exclude='cache_huggingface/'", # Excluir cache de modelos
    "--exclude='node_modules/'", # Excluir node_modules
    "--exclude='.vscode/'",    # Excluir configuración de VS Code
    "--exclude='*.log'",       # Excluir archivos de log
    "--exclude='.DS_Store'",   # Excluir archivos de macOS
    "--exclude='Thumbs.db'"    # Excluir archivos de Windows
)

if ($DryRun) {
    $RsyncOptions += "--dry-run"
    Write-Host "⚠️  MODO DRY-RUN (solo mostrando cambios, no sincronizando)"
    Write-Host ""
}

# ========================================
# EJECUTAR RSYNC
# ========================================
Write-Host "Ejecutando rsync..."
Write-Host ""

# Detectar si hay rsync disponible
$RsyncPath = $null

if (Get-Command wsl -ErrorAction SilentlyContinue) {
    # Opción 1: Usar WSL
    Write-Host "Usando rsync de WSL..."
    $LocalPathWSL = $LocalPath -replace '\\', '/' -replace 'C:', '/mnt/c'
    wsl rsync $RsyncOptions "$LocalPathWSL" "${RemoteUser}@${RemoteHost}:${RemotePath}"
    $RsyncExitCode = $LASTEXITCODE
} elseif (Test-Path "C:\Program Files\Git\usr\bin\rsync.exe") {
    # Opción 2: Usar rsync de Git Bash
    Write-Host "Usando rsync de Git for Windows..."
    $RsyncPath = "C:\Program Files\Git\usr\bin\rsync.exe"
    & $RsyncPath $RsyncOptions "$LocalPath" "${RemoteUser}@${RemoteHost}:${RemotePath}"
    $RsyncExitCode = $LASTEXITCODE
} else {
    Write-Host "❌ ERROR: rsync no encontrado"
    Write-Host ""
    Write-Host "Instala una de estas opciones:"
    Write-Host "1. WSL (Windows Subsystem for Linux):"
    Write-Host "   wsl --install"
    Write-Host ""
    Write-Host "2. Git for Windows (incluye rsync):"
    Write-Host "   https://git-scm.com/download/win"
    Write-Host ""
    exit 1
}

# ========================================
# VERIFICAR RESULTADO
# ========================================
Write-Host ""
if ($RsyncExitCode -eq 0) {
    Write-Host "=========================================="
    Write-Host "✅ Sincronización completada exitosamente"
    Write-Host "=========================================="
} else {
    Write-Host "=========================================="
    Write-Host "❌ Error en la sincronización (código: $RsyncExitCode)"
    Write-Host "=========================================="
    exit $RsyncExitCode
}

# ========================================
# REINICIAR SERVICIOS (OPCIONAL)
# ========================================
if ($Restart -and -not $DryRun) {
    Write-Host ""
    Write-Host "Reiniciando servicios en el servidor..."
    ssh "${RemoteUser}@${RemoteHost}" "/opt/Dahell/scripts/update.sh"
}

# ========================================
# PRÓXIMOS PASOS
# ========================================
Write-Host ""
Write-Host "Próximos pasos:"
Write-Host ""
Write-Host "1. Reiniciar servicios (si es necesario):"
Write-Host "   ssh ${RemoteUser}@${RemoteHost} '/opt/Dahell/scripts/update.sh'"
Write-Host ""
Write-Host "2. Ver logs en tiempo real:"
Write-Host "   ssh ${RemoteUser}@${RemoteHost} 'docker compose -f /opt/Dahell/docker-compose.production.yml logs -f'"
Write-Host ""
Write-Host "3. Ver estado de servicios:"
Write-Host "   ssh ${RemoteUser}@${RemoteHost} 'docker ps'"
Write-Host ""
