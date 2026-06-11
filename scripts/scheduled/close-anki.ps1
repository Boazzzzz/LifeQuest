$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

& ".\.venv\Scripts\python.exe" -m app.cli automation run-scheduled close-anki
