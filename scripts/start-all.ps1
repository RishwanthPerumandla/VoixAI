param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

$services = @(
    @{
        Name = "VoixAI API"
        WorkingDirectory = Join-Path $repoRoot "apps\api"
        RequiredPaths = @(".venv\Scripts\python.exe")
        Command = "& '.\.venv\Scripts\python.exe' -m uvicorn main:app --reload --port 8000"
    },
    @{
        Name = "VoixAI Agent Runtime"
        WorkingDirectory = Join-Path $repoRoot "apps\agent-runtime"
        RequiredPaths = @(".venv\Scripts\python.exe")
        Command = "& '.\.venv\Scripts\python.exe' .\src\agent.py dev"
    },
    @{
        Name = "VoixAI Web"
        WorkingDirectory = Join-Path $repoRoot "apps\web"
        RequiredPaths = @("node_modules")
        Command = "corepack pnpm dev"
    }
)

function Test-ServiceRequirements {
    param(
        [hashtable]$Service
    )

    foreach ($requiredPath in $Service.RequiredPaths) {
        $fullPath = Join-Path $Service.WorkingDirectory $requiredPath
        if (-not (Test-Path -LiteralPath $fullPath)) {
            throw "$($Service.Name) is missing required path: $fullPath"
        }
    }
}

function New-ServiceCommand {
    param(
        [hashtable]$Service
    )

    $escapedDirectory = $Service.WorkingDirectory.Replace("'", "''")
    $escapedName = $Service.Name.Replace("'", "''")

    @"
Set-Location '$escapedDirectory'
Write-Host "Starting $escapedName..." -ForegroundColor Cyan
$($Service.Command)
"@
}

foreach ($service in $services) {
    Test-ServiceRequirements -Service $service
}

if ($DryRun) {
    foreach ($service in $services) {
        Write-Host "$($service.Name): $($service.WorkingDirectory)" -ForegroundColor Yellow
        Write-Host "  $($service.Command)"
    }
    exit 0
}

foreach ($service in $services) {
    $childCommand = New-ServiceCommand -Service $service
    Start-Process -FilePath "powershell.exe" -WorkingDirectory $service.WorkingDirectory -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $childCommand
    )
}

Write-Host "VoixAI services launched in separate PowerShell windows." -ForegroundColor Green
Write-Host "API: http://127.0.0.1:8000/health"
Write-Host "Web: http://localhost:3000"
