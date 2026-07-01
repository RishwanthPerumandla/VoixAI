Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$apiDir = Join-Path $repoRoot "apps\api"
$python = Join-Path $apiDir ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

Push-Location $apiDir
try {
    & $python -m seed
}
finally {
    Pop-Location
}
