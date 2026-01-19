# Start classifiers and collect their logs to files in ../logs
param(
    [switch]$TailAfterStart
)

# Desc: Levanta los servicios classifier y classifier_2 y guarda sus logs en archivos bajo logs/.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$logsDir = Join-Path $scriptDir "..\logs"
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }

Write-Output "Starting classifier services with docker compose..."
# Usar docker compose (v2) o docker-compose según esté disponible
try {
    docker compose up -d classifier classifier_2 2>&1 | Write-Output
} catch {
    docker-compose up -d classifier classifier_2 2>&1 | Write-Output
}

Start-Sleep -Seconds 2

Write-Output "Starting background jobs to collect container logs into $logsDir"

$collector = {
    param($containerName, $outFile)
    # Reintentar si docker no está listo
    while ($true) {
        try {
            docker logs -f $containerName | Out-File -FilePath $outFile -Encoding utf8
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
}

$job1 = Start-Job -ScriptBlock $collector -ArgumentList 'dahell_classifier', (Join-Path $logsDir 'dahell_classifier.log')
$job2 = Start-Job -ScriptBlock $collector -ArgumentList 'dahell_classifier_2', (Join-Path $logsDir 'dahell_classifier_2.log')

Write-Output "Log collection started. Job IDs: $($job1.Id), $($job2.Id)"

if ($TailAfterStart) {
    Write-Output "Tailing dahell_classifier from log file (stop with Ctrl+C)"
    $tailFile = (Join-Path $logsDir 'dahell_classifier.log')
    if (Test-Path $tailFile) {
        Get-Content -Path $tailFile -Wait -Tail 100
    } else {
        Write-Output "Log file not found: $tailFile"
    }
}

Write-Output "Script finished. Use Get-Job and Receive-Job to monitor jobs, or check files in $logsDir"