param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

function Get-ListenerProcessIds {
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

    return @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Test-LifeQuestHealth {
    param([int]$PortNumber)

    try {
        $response = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/health" -f $PortNumber) -TimeoutSec 2
        return $response.status -eq "ok"
    }
    catch {
        return $false
    }
}

function Get-ProcessCommandLine {
    param([int]$ProcessId)

    try {
        $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        return $processInfo.CommandLine
    }
    catch {
        return ""
    }
}

$processIds = @(Get-ListenerProcessIds -PortNumber $Port)
if ($processIds.Count -eq 0) {
    Write-Host "No process is listening on port $Port."
    exit 0
}

$stopped = 0
$isLifeQuestHealthy = Test-LifeQuestHealth -PortNumber $Port
foreach ($processId in $processIds) {
    $commandLine = Get-ProcessCommandLine -ProcessId $processId
    if ($isLifeQuestHealthy -or ($commandLine -match "uvicorn" -and $commandLine -match "app\.main:app")) {
        Stop-Process -Id $processId -ErrorAction Stop
        Write-Host "Stopped LifeQuest backend process PID $processId."
        $stopped += 1
        continue
    }

    Write-Host "PID $processId is listening on port $Port, but it does not look like LifeQuest/uvicorn. Leaving it running."
}

if ($stopped -eq 0) {
    exit 2
}

exit 0
