# Enable Docker Desktop WSL integration (settings-store.json), then restart Docker Desktop.
$ErrorActionPreference = "Stop"
$p = Join-Path ([Environment]::GetFolderPath("ApplicationData")) "Docker\settings-store.json"
$j = Get-Content $p -Raw | ConvertFrom-Json
$j | Add-Member -NotePropertyName "WslEngineEnabled" -NotePropertyValue $true -Force
$j | ConvertTo-Json | Set-Content $p -Encoding UTF8
Write-Output "--- settings-store.json ---"
Get-Content $p

# Restart Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Write-Output "Docker Desktop restarting..."
