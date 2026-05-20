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

$taskCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $startScript
$ErrorActionPreference = "Continue"
& schtasks.exe /Create /TN $TaskName /SC ONLOGON /TR $taskCommand /F /RL LIMITED | Out-Host
$exitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($exitCode -ne 0) {
    throw "Failed to register startup task: $TaskName. If Windows reports access denied, run this script from a normal elevated PowerShell session or create the task manually in Task Scheduler."
}

Write-Host "Registered startup task: $TaskName"
