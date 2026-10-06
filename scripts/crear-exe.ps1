# Compila el lanzador y lo deja en el Escritorio como "Ejercicios LaTeX.exe".
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$csc = Get-ChildItem "$env:WINDIR\Microsoft.NET\Framework64\v4*\csc.exe" | Select-Object -First 1 -ExpandProperty FullName
if (-not $csc) { throw "No se encuentra csc.exe (.NET Framework)." }
$tmp = Join-Path $env:TEMP "lanzador-ejercicios"
New-Item -ItemType Directory -Force $tmp | Out-Null
$fuente = Join-Path $tmp "Lanzador.cs"
$cs = (Get-Content (Join-Path $PSScriptRoot "Lanzador.cs") -Raw -Encoding UTF8).Replace("__PROYECTO__", $root)
[IO.File]::WriteAllText($fuente, $cs, (New-Object Text.UTF8Encoding $true))
$destino = Join-Path ([Environment]::GetFolderPath("Desktop")) "Ejercicios LaTeX.exe"
& $csc /nologo /target:exe /out:$destino $fuente
if ($LASTEXITCODE -ne 0) { throw "La compilacion del lanzador fallo." }
Write-Host "Creado: $destino"
