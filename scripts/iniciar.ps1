# Levanta el backend (API real) y el frontend (produccion) en local y abre el navegador.
# Solo escucha en 127.0.0.1: no se expone a la red. Al pulsar Enter (o cerrar la ventana) se apaga todo.
# -Prueba: arranca, comprueba que responde, apaga y sale (para verificar el script sin dejar nada abierto).
param([switch]$Prueba, [switch]$SinNavegador)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$back = Join-Path $root "backend"
$front = Join-Path $root "frontend"
$logs = Join-Path $env:TEMP "ejercicios-latex"
New-Item -ItemType Directory -Force $logs | Out-Null
$procs = @()

function Escucha($puerto) {
    [bool](Get-NetTCPConnection -State Listen -LocalPort $puerto -ErrorAction SilentlyContinue)
}
function Responde($url) {
    try { (Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 } catch { $false }
}
function Esperar($url, $nombre, $segundos) {
    $fin = (Get-Date).AddSeconds($segundos)
    while ((Get-Date) -lt $fin) {
        if (Responde $url) { return }
        Start-Sleep -Milliseconds 700
    }
    throw "$nombre no respondio en $segundos s. Mira los registros en $logs"
}
function Apagar {
    foreach ($p in $procs) {
        if ($p -and -not $p.HasExited) { & taskkill.exe /PID $p.Id /T /F 2>&1 | Out-Null }
    }
}

try {
    Write-Host ""
    Write-Host "  Ejercicios LaTeX" -ForegroundColor Cyan
    Write-Host "  ----------------"

    foreach ($puerto in 8000, 3000) {
        if (Escucha $puerto) {
            throw "El puerto $puerto ya esta en uso (quiza ya hay una copia en marcha). Cierrala e intentalo de nuevo."
        }
    }
    if (-not (Test-Path (Join-Path $back ".env"))) { throw "Falta backend\.env con la clave de la API (ver backend\.env.example)." }
    if (-not (Test-Path (Join-Path $back ".venv\Scripts\python.exe"))) { throw "Falta el entorno de Python en backend\.venv." }

    # Reconstruye el frontend solo si el codigo es mas nuevo que la ultima compilacion.
    $buildId = Join-Path $front ".next\BUILD_ID"
    $fuentes = "app", "components", "lib", "public", "next.config.ts", "package.json" | ForEach-Object { Join-Path $front $_ }
    $ultimoCambio = Get-ChildItem $fuentes -Recurse -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not (Test-Path $buildId) -or $ultimoCambio.LastWriteTime -gt (Get-Item $buildId).LastWriteTime) {
        Write-Host "  Compilando la interfaz (solo hace falta tras cambios, ~1 min)..." -ForegroundColor Yellow
        Push-Location $front
        & npm.cmd run build *> (Join-Path $logs "build.log")
        $fallo = $LASTEXITCODE -ne 0
        Pop-Location
        if ($fallo) { throw "La compilacion fallo. Mira $logs\build.log" }
    }

    Write-Host "  Arrancando el servidor (backend)..."
    $procs += Start-Process -FilePath (Join-Path $back ".venv\Scripts\python.exe") `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory $back -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logs "backend.out.log") -RedirectStandardError (Join-Path $logs "backend.err.log")

    Write-Host "  Arrancando la interfaz (frontend)..."
    $procs += Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c", "npm run start -- -H 127.0.0.1" `
        -WorkingDirectory $front -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logs "frontend.out.log") -RedirectStandardError (Join-Path $logs "frontend.err.log")

    Esperar "http://127.0.0.1:8000/api/health" "El backend" 60
    Esperar "http://127.0.0.1:3000/scan" "La interfaz" 60

    Write-Host ""
    Write-Host "  Todo listo: http://127.0.0.1:3000/scan" -ForegroundColor Green
    if ($Prueba) {
        Write-Host "  (modo prueba: apagando)"
    } else {
        if (-not $SinNavegador) { Start-Process "http://127.0.0.1:3000/scan" }
        Write-Host "  Usa la API de pago real. Pulsa Enter (o cierra esta ventana) para apagar todo."
        [void][Console]::ReadLine()
    }
}
catch {
    Write-Host ""
    Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
    if (-not $Prueba) { Write-Host "  Pulsa Enter para cerrar."; [void][Console]::ReadLine() }
    $global:LASTEXITCODE = 1
}
finally {
    Apagar
}
if ($global:LASTEXITCODE -eq 1) { exit 1 }
