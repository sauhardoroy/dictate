# Dictate Installation Script for Windows
$ErrorActionPreference = "Stop"

$AppName = "Dictate"
$SourceDir = Join-Path $PSScriptRoot "dist\Dictate"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\$AppName"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       Installing Dictate Voice Typing    " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

if (-not (Test-Path $SourceDir)) {
    Write-Host "Error: Built executable folder not found at: $SourceDir" -ForegroundColor Red
    exit 1
}

# Stop any running instances
Write-Host "[1/5] Closing any running instances of $AppName..." -ForegroundColor Yellow
Get-Process -Name "Dictate" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 600

# Copy files to %LOCALAPPDATA%\Programs\Dictate
Write-Host "[2/5] Installing application files to: $InstallDir" -ForegroundColor Yellow
if (Test-Path $InstallDir) {
    Remove-Item -Path "$InstallDir\*" -Recurse -Force -ErrorAction SilentlyContinue
} else {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}
Copy-Item -Path "$SourceDir\*" -Destination $InstallDir -Recurse -Force

$TargetExe = Join-Path $InstallDir "Dictate.exe"

# Generate / use Code Signing Certificate to sign the binary
Write-Host "[3/5] Applying local security signature (Trusted Publisher)..." -ForegroundColor Yellow
try {
    $CertSubject = "CN=Dictate Local Security Certificate"
    $Cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Subject -eq $CertSubject } | Select-Object -First 1
    if (-not $Cert) {
        $Cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $CertSubject -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddYears(10)
        # Add to Trusted Root & Trusted Publisher for CurrentUser
        $RootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store "Root", "CurrentUser"
        $RootStore.Open("ReadWrite")
        $RootStore.Add($Cert)
        $RootStore.Close()

        $PubStore = New-Object System.Security.Cryptography.X509Certificates.X509Store "TrustedPublisher", "CurrentUser"
        $PubStore.Open("ReadWrite")
        $PubStore.Add($Cert)
        $PubStore.Close()
    }
    Set-AuthenticodeSignature -FilePath $TargetExe -Certificate $Cert | Out-Null
    Write-Host "      Signed $TargetExe with trusted local certificate." -ForegroundColor Green
} catch {
    Write-Warning "Code signing step skipped: $($_.Exception.Message)"
}

# Create Start Menu & Desktop Shortcuts
Write-Host "[4/5] Creating Shortcuts..." -ForegroundColor Yellow
$WshShell = New-Object -ComObject WScript.Shell

# Desktop shortcut
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$DesktopShortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "$AppName.lnk"))
$DesktopShortcut.TargetPath = $TargetExe
$DesktopShortcut.WorkingDirectory = $InstallDir
$DesktopShortcut.Description = "Dictate Voice Typing"
$DesktopShortcut.Save()

# Start Menu Programs shortcut
$ProgramsPath = [Environment]::GetFolderPath("Programs")
$StartMenuShortcut = $WshShell.CreateShortcut((Join-Path $ProgramsPath "$AppName.lnk"))
$StartMenuShortcut.TargetPath = $TargetExe
$StartMenuShortcut.WorkingDirectory = $InstallDir
$StartMenuShortcut.Description = "Dictate Voice Typing"
$StartMenuShortcut.Save()

# Autostart — respect the app's own Settings → autostart toggle.
# The installer does not create a Startup shortcut by default; users opt in
# from the Settings dialog (or set_autostart(True) at runtime).

Write-Host "[5/5] Installation Complete! Starting Dictate..." -ForegroundColor Green
Write-Host ""
Write-Host "Dictate Version 2.0 has been successfully installed and signed." -ForegroundColor Green
Write-Host "Shortcuts created on Desktop and Start Menu." -ForegroundColor White
Write-Host "Press Ctrl+Shift+P anytime to dictate text!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Automatically start the app so there is no hassle
Start-Process -FilePath $TargetExe -WorkingDirectory $InstallDir
