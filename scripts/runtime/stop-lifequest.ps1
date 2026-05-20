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
        return @()
    }

    return @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
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
foreach ($processId in $processIds) {
    $commandLine = Get-ProcessCommandLine -ProcessId $processId
    if ($commandLine -match "uvicorn" -and $commandLine -match "app\.main:app") {
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
