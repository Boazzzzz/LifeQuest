param(
    [string]$TaskName = "LifeQuest Backend"
)

$ErrorActionPreference = "Stop"

$ErrorActionPreference = "Continue"
& schtasks.exe /Query /TN $TaskName *> $null
$queryExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($queryExitCode -ne 0) {
    Write-Host "Startup task is not registered: $TaskName"
    exit 0
}

$ErrorActionPreference = "Continue"
& schtasks.exe /Delete /TN $TaskName /F | Out-Host
$deleteExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($deleteExitCode -ne 0) {
    throw "Failed to unregister startup task: $TaskName"
}

Write-Host "Unregistered startup task: $TaskName"
