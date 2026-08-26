# Dictate Uninstaller Script for Windows
$ErrorActionPreference = "Continue"

$AppName = "Dictate"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\$AppName"

Write-Host "Uninstalling Dictate..." -ForegroundColor Yellow
Get-Process -Name "Dictate" -ErrorAction SilentlyContinue | Stop-Process -Force

# Remove shortcuts, including Startup if the user enabled autostart.
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "$AppName.lnk"
$StartMenuShortcut = Join-Path ([Environment]::GetFolderPath("Programs")) "$AppName.lnk"
$StartupShortcut = Join-Path ([Environment]::GetFolderPath("Startup")) "$AppName.lnk"

Remove-Item $DesktopShortcut -Force -ErrorAction SilentlyContinue
Remove-Item $StartMenuShortcut -Force -ErrorAction SilentlyContinue
Remove-Item $StartupShortcut -Force -ErrorAction SilentlyContinue

# Remove install directory.
if (Test-Path $InstallDir) {
    Remove-Item -Path $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Dictate has been uninstalled." -ForegroundColor Green
