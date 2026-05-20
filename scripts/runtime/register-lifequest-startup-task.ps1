param(
    [string]$TaskName = "LifeQuest Backend"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$startScript = Join-Path $PSScriptRoot "start-lifequest.ps1"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Missing virtualenv Python at $python. Create the venv and install dependencies first: python -m venv .venv; python -m pip install -e `".[dev]`""
}

if (-not (Test-Path -LiteralPath $startScript)) {
    Write-Error "Missing startup script at $startScript."
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal `
    -UserId $currentUser `
    -LogonType Interactive `
    -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Write-Host "Registered startup task: $TaskName"
