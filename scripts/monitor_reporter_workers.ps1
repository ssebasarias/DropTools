# Monitor de logs del worker Celery para el reporter por slot.
# Modo filtrado: solo líneas con tareas/user_id/run_id/semáforo.
# Modo completo (-All): todas las líneas (qué hace cada uno de los 6 workers en tiempo real).
# Modo por worker (-Worker N): solo líneas del ForkPoolWorker-N (para abrir 6 terminales, una por worker).
# Complementa Flower: http://localhost:5555
#
# Uso:
#   .\scripts\monitor_reporter_workers.ps1              # filtrado (solo tareas y run_id)
#   .\scripts\monitor_reporter_workers.ps1 -All          # TODO en tiempo real (6 workers)
#   .\scripts\monitor_reporter_workers.ps1 -Worker 1    # solo worker 1 (abre 6 terminales con -Worker 1..6)
#   .\scripts\monitor_reporter_workers.ps1 -Filter "..." # filtro personalizado
#
# Ver los 6 workers en simultáneo: abre 6 terminales y en cada una:
#   .\scripts\monitor_reporter_workers.ps1 -Worker 1   # terminal 1
#   .\scripts\monitor_reporter_workers.ps1 -Worker 2   # terminal 2
#   ... hasta -Worker 6
#
# Ejecutar desde la raíz del proyecto (donde está docker-compose.yml).

param(
    [string]$Filter = "download_compare_task|report_range_task|user_id|run_id|semaphore|ReporterRange|process_slot",
    [switch]$All,
    [int]$Worker = 0
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
if (-not (Test-Path (Join-Path $projectRoot "docker-compose.yml"))) {
    Write-Error "No se encontró docker-compose.yml en $projectRoot. Ejecuta desde la raíz del proyecto."
}

Push-Location $projectRoot
try {
    $workerPattern = if ($Worker -ge 1 -and $Worker -le 6) { "ForkPoolWorker-$Worker\b" } else { $null }

    if ($workerPattern) {
        Write-Host "Monitoreando celery_worker - solo Worker $Worker (Ctrl+C para salir)" -ForegroundColor Cyan
        Write-Host "Para ver los 6: abre 6 terminales y usa -Worker 1, -Worker 2, ... -Worker 6" -ForegroundColor Gray
        Write-Host "Flower: http://localhost:5555" -ForegroundColor Gray
        docker compose logs -f celery_worker 2>&1 | ForEach-Object -Process {
            if ($_ -match $workerPattern) { $_ }
        }
    } elseif ($All) {
        Write-Host "Monitoreando celery_worker - TODOS los logs (6 workers, Ctrl+C para salir)" -ForegroundColor Cyan
        Write-Host "Flower: http://localhost:5555" -ForegroundColor Gray
        docker compose logs -f celery_worker
    } else {
        Write-Host "Monitoreando celery_worker (Ctrl+C para salir). Filtro: $Filter" -ForegroundColor Cyan
        Write-Host "Para ver todo: .\scripts\monitor_reporter_workers.ps1 -All" -ForegroundColor Gray
        Write-Host "Para un worker: .\scripts\monitor_reporter_workers.ps1 -All -Worker 1" -ForegroundColor Gray
        Write-Host "Flower: http://localhost:5555" -ForegroundColor Gray
        docker compose logs -f celery_worker 2>&1 | ForEach-Object -Process {
            if ($_ -match $Filter) { $_ }
        }
    }
} finally {
    Pop-Location
}
