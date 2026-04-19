# NSIS Installation Script for Evolver
# Run this script as Administrator to install NSIS

$ErrorActionPreference = "Stop"

# Configuration
$NSIS_VERSION = "3.10"
$NSIS_URL = "https://downloads.sourceforge.net/project/nsis/NSIS%20${NSIS_VERSION}/nsis-${NSIS_VERSION}.zip"
$INSTALL_DIR = "C:\Program Files (x86)\NSIS"
$TEMP_DIR = "$env:TEMP\nsis_install"

Write-Host "=== Evolver NSIS Installer ===" -ForegroundColor Cyan
Write-Host "Version: $NSIS_VERSION"
Write-Host ""

# Check if NSIS is already installed
$nsisPath = "$INSTALL_DIR\makensis.exe"
if (Test-Path $nsisPath) {
    Write-Host "NSIS is already installed at: $INSTALL_DIR" -ForegroundColor Green
    Write-Host "Verifying installation..."
    & $nsisPath /VERSION
    exit 0
}

# Create temp directory
Write-Host "Creating temporary directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $TEMP_DIR | Out-Null

# Download NSIS
Write-Host "Downloading NSIS $NSIS_VERSION..." -ForegroundColor Yellow
Write-Host "URL: $NSIS_URL"
$zipPath = "$TEMP_DIR\nsis.zip"

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $NSIS_URL -OutFile $zipPath -UseBasicParsing -TimeoutSec 120
    Write-Host "Download completed!" -ForegroundColor Green
} catch {
    Write-Host "Download failed: $_" -ForegroundColor Red
    Write-Host "Please download manually from: https://nsis.sourceforge.io/Download" -ForegroundColor Yellow
    exit 1
}

# Extract NSIS
Write-Host "Extracting NSIS..." -ForegroundColor Yellow
Expand-Archive -Path $zipPath -DestinationPath $TEMP_DIR -Force
$extractedDir = Get-ChildItem -Path $TEMP_DIR -Directory | Where-Object { $_.Name -like "nsis*" } | Select-Object -First 1

if (-not $extractedDir) {
    Write-Host "Extraction failed!" -ForegroundColor Red
    exit 1
}

# Move to installation directory
Write-Host "Installing NSIS to: $INSTALL_DIR" -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null
Copy-Item -Path "$($extractedDir.FullName)\*" -Destination $INSTALL_DIR -Recurse -Force

# Add to PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$INSTALL_DIR*") {
    Write-Host "Adding NSIS to PATH..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$INSTALL_DIR", "User")
    $env:Path = "$env:Path;$INSTALL_DIR"
}

# Cleanup
Write-Host "Cleaning up..." -ForegroundColor Yellow
Remove-Item -Path $TEMP_DIR -Recurse -Force

# Verify installation
Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Green
Write-Host "NSIS installed to: $INSTALL_DIR"
Write-Host ""
Write-Host "Verifying makensis..." -ForegroundColor Yellow
& "$INSTALL_DIR\makensis.exe" /VERSION

Write-Host ""
Write-Host "Now you can build the Tauri application with:" -ForegroundColor Cyan
Write-Host "  cd frontend" -ForegroundColor White
Write-Host "  npm run tauri:build" -ForegroundColor White
