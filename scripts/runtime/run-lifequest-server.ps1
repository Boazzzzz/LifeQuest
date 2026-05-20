param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,

    [Parameter(Mandatory = $true)]
    [string]$PythonPath,

    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,

    [Parameter(Mandatory = $true)]
    [string]$LogPath
)

$ErrorActionPreference = "Stop"

$logDir = Split-Path -Parent $LogPath
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
Set-Location -LiteralPath $RepoRoot

& $PythonPath -m uvicorn app.main:app --host $BindHost --port $Port *>> $LogPath
