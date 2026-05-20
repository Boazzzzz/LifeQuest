param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

function Test-LifeQuestHealth {
    param(
        [string]$HostName,
        [int]$PortNumber
    )

    $healthUrl = "http://{0}:{1}/health" -f $HostName, $PortNumber
    try {
        $response = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        return $response.status -eq "ok"
    }
    catch {
        return $false
    }
}

function Get-LifeQuestListeners {
    param([int]$PortNumber)

    try {
        return @(Get-NetTCPConnection -LocalPort $PortNumber -State Listen -ErrorAction Stop)
    }
    catch {
        return @()
    }
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$logDir = Join-Path $repoRoot "data\logs"
$logPath = Join-Path $logDir ("lifequest-server-{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))
$dashboardUrl = "http://{0}:{1}/dashboard" -f $BindHost, $Port

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Missing virtualenv Python at $python. Create the venv and install dependencies first: python -m venv .venv; python -m pip install -e `".[dev]`""
}

if (Test-LifeQuestHealth -HostName $BindHost -PortNumber $Port) {
    Write-Host "LifeQuest is already running at $dashboardUrl"
    exit 0
}

$listeners = Get-LifeQuestListeners -PortNumber $Port
if ($listeners.Count -gt 0) {
    Write-Error "Port $Port is already in use, but LifeQuest health check did not pass. Run scripts\runtime\status-lifequest.ps1 for details."
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$command = @"
`$ErrorActionPreference = "Stop"
Set-Location -LiteralPath "$repoRoot"
& "$python" -m uvicorn app.main:app --host "$BindHost" --port $Port *>> "$logPath"
"@

$encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
$process = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encodedCommand) `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden `
    -PassThru

for ($attempt = 1; $attempt -le 20; $attempt++) {
    Start-Sleep -Milliseconds 500
    if (Test-LifeQuestHealth -HostName $BindHost -PortNumber $Port) {
        Write-Host "LifeQuest started at $dashboardUrl"
        Write-Host "Log: $logPath"
        exit 0
    }
}

Write-Error "LifeQuest process started as PID $($process.Id), but /health did not become ready. Check log: $logPath"
