param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$dashboardUrl = "http://{0}:{1}/dashboard" -f $BindHost, $Port
Start-Process $dashboardUrl
Write-Host "Opened $dashboardUrl"
