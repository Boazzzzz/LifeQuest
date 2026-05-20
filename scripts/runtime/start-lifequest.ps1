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
        $connections = @(Get-NetTCPConnection -LocalPort $PortNumber -State Listen -ErrorAction Stop)
        if ($connections.Count -gt 0) {
            return $connections
        }
    }
    catch {
    }

    $listeners = @()
    $lines = @(netstat -ano -p tcp | Select-String "LISTENING")
    foreach ($line in $lines) {
        $parts = @($line.Line -split "\s+" | Where-Object { $_ })
        if ($parts.Count -ge 5 -and $parts[1] -match ":$PortNumber$") {
            $listeners += [pscustomobject]@{
                LocalAddress = $parts[1]
                LocalPort = $PortNumber
                OwningProcess = [int]$parts[4]
            }
        }
    }

    return $listeners
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$runner = Join-Path $PSScriptRoot "run-lifequest-server.ps1"
$logDir = Join-Path $repoRoot "data\logs"
$logPath = Join-Path $logDir ("lifequest-server-{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))
$dashboardUrl = "http://{0}:{1}/dashboard" -f $BindHost, $Port

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Missing virtualenv Python at $python. Create the venv and install dependencies first: python -m venv .venv; python -m pip install -e `".[dev]`""
}

if (-not (Test-Path -LiteralPath $runner)) {
    Write-Error "Missing runtime runner at $runner."
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

$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "`"$runner`"",
    "-RepoRoot",
    "`"$repoRoot`"",
    "-PythonPath",
    "`"$python`"",
    "-BindHost",
    $BindHost,
    "-Port",
    $Port.ToString(),
    "-LogPath",
    "`"$logPath`""
)

$process = Start-Process -FilePath "powershell.exe" `
    -ArgumentList $arguments `
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
