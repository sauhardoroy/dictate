# Dictate C++ Native Windows Installation Script
$ErrorActionPreference = "Stop"

$AppName = "DictateCpp"
$SourceExe = Join-Path $PSScriptRoot "bin\dictate_cpp.exe"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\$AppName"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "    Installing Dictate C++ Native App     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if (-not (Test-Path $SourceExe)) {
    Write-Host "Error: Built executable not found at: $SourceExe" -ForegroundColor Red
    exit 1
}

# Stop any running instances
Write-Host "[1/4] Closing running instances of $AppName..." -ForegroundColor Yellow
Get-Process -Name "dictate_cpp" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 400

# Copy files
Write-Host "[2/4] Installing application to: $InstallDir" -ForegroundColor Yellow
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}
Copy-Item -Path $SourceExe -Destination (Join-Path $InstallDir "dictate_cpp.exe") -Force

$TargetExe = Join-Path $InstallDir "dictate_cpp.exe"

# Create Desktop & Start Menu Shortcuts
Write-Host "[3/4] Creating Shortcuts..." -ForegroundColor Yellow
$WshShell = New-Object -ComObject WScript.Shell

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$DesktopShortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "Dictate C++.lnk"))
$DesktopShortcut.TargetPath = $TargetExe
$DesktopShortcut.WorkingDirectory = $InstallDir
$DesktopShortcut.Description = "Dictate C++ Native Voice Typing"
$DesktopShortcut.Save()

$ProgramsPath = [Environment]::GetFolderPath("Programs")
$StartMenuShortcut = $WshShell.CreateShortcut((Join-Path $ProgramsPath "Dictate C++.lnk"))
$StartMenuShortcut.TargetPath = $TargetExe
$StartMenuShortcut.WorkingDirectory = $InstallDir
$StartMenuShortcut.Description = "Dictate C++ Native Voice Typing"
$StartMenuShortcut.Save()

Write-Host "[4/4] Installation Complete! Starting Dictate C++..." -ForegroundColor Green
Write-Host ""
Write-Host "Dictate C++ installed successfully (Size: ~112 KB, 120 FPS Direct2D)." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

Start-Process -FilePath $TargetExe -WorkingDirectory $InstallDir
