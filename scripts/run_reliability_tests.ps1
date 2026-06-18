Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $repoRoot "apps\\agent-runtime"
$python = Join-Path $runtimeRoot ".venv\\Scripts\\python.exe"

if (-not (Test-Path $python)) {
    throw "Expected runtime venv interpreter at $python"
}

Push-Location $runtimeRoot
try {
    & $python -m pytest tests/reliability -q
}
finally {
    Pop-Location
}
