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

function Get-ListenerProcesses {
    param([int]$PortNumber)

    try {
        $connections = @(Get-NetTCPConnection -LocalPort $PortNumber -State Listen -ErrorAction Stop)
    }
    catch {
        $connections = @()
    }

    if ($connections.Count -eq 0) {
        $lines = @(netstat -ano -p tcp | Select-String "LISTENING")
        foreach ($line in $lines) {
            $parts = @($line.Line -split "\s+" | Where-Object { $_ })
            if ($parts.Count -ge 5 -and $parts[1] -match ":$PortNumber$") {
                $connections += [pscustomobject]@{
                    OwningProcess = [int]$parts[4]
                }
            }
        }
    }

    $processIds = @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
    $processes = @()
    foreach ($processId in $processIds) {
        try {
            $processes += Get-Process -Id $processId -ErrorAction Stop
        }
        catch {
        }
    }
    return $processes
}

$dashboardUrl = "http://{0}:{1}/dashboard" -f $BindHost, $Port
$isHealthy = Test-LifeQuestHealth -HostName $BindHost -PortNumber $Port
$listeners = @(Get-ListenerProcesses -PortNumber $Port)

if ($isHealthy) {
    Write-Host "LifeQuest is healthy at $dashboardUrl"
    if ($listeners.Count -gt 0) {
        foreach ($process in $listeners) {
            Write-Host ("Listener: PID {0} {1}" -f $process.Id, $process.ProcessName)
        }
    }
    exit 0
}

if ($listeners.Count -gt 0) {
    Write-Host "Port $Port has a listener, but LifeQuest /health is not healthy."
    foreach ($process in $listeners) {
        Write-Host ("Listener: PID {0} {1}" -f $process.Id, $process.ProcessName)
    }
    exit 2
}

Write-Host "LifeQuest is not running on $BindHost`:$Port"
exit 1
