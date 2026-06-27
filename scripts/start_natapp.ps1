param(
    [string]$NatappPath = "",
    [string]$AuthToken = "",
    [int]$BackendPort = 8009
)

$ErrorActionPreference = "Stop"

function Find-Natapp {
    param([string]$ExplicitPath)

    if ($ExplicitPath -and (Test-Path $ExplicitPath -PathType Leaf)) {
        return (Resolve-Path $ExplicitPath).Path
    }

    $command = Get-Command natapp -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidates = @(
        ".\tools\natapp\natapp.exe",
        ".\natapp.exe",
        "$env:USERPROFILE\Downloads\natapp.exe",
        "$env:USERPROFILE\Desktop\natapp.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate -PathType Leaf)) {
            return (Resolve-Path $candidate).Path
        }
    }

    return ""
}

$natapp = Find-Natapp -ExplicitPath $NatappPath
if (!$natapp) {
    Write-Host "NATAPP client was not found." -ForegroundColor Red
    Write-Host "Put natapp.exe at tools\natapp\natapp.exe, or pass -NatappPath C:\path\to\natapp.exe."
    Write-Host "Official install command: powershell -c `"irm 'https://natapp.cn/get.ps1?authtoken=<your-token>' | iex`""
    exit 1
}

if (!$AuthToken) {
    $AuthToken = $env:NATAPP_AUTHTOKEN
}

if (!$AuthToken) {
    $AuthToken = Read-Host "Enter NATAPP authtoken"
}

try {
    Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$BackendPort/health" -TimeoutSec 5 | Out-Null
} catch {
    Write-Host "Backend is not reachable at http://127.0.0.1:$BackendPort/health." -ForegroundColor Red
    Write-Host "Start the backend first: cd backend; python run.py"
    exit 1
}

Write-Host "Starting NATAPP..." -ForegroundColor Green
Write-Host "NATAPP dashboard tunnel target must be 127.0.0.1:$BackendPort"
Write-Host "Press Ctrl+C here to stop the tunnel."
Write-Host ""

& $natapp "-authtoken=$AuthToken"
