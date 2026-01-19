# ATF Tools Installer for Windows
# Run with: powershell -ExecutionPolicy Bypass -File install.ps1

Write-Host "Installing ATF Tools..." -ForegroundColor Green

# Get latest version
$LatestUrl = "https://api.github.com/repos/atf-tools/atf/releases/latest"
$Release = Invoke-RestMethod -Uri $LatestUrl
$Version = $Release.tag_name

if (-not $Version) {
    Write-Host "Error: Could not determine latest version" -ForegroundColor Red
    exit 1
}

Write-Host "Latest version: $Version" -ForegroundColor Cyan

# Download URL
$BinaryName = "atf-windows-amd64.exe"
$DownloadUrl = "https://github.com/atf-tools/atf/releases/download/$Version/$BinaryName"

# Installation directory
$InstallDir = "$env:LOCALAPPDATA\ATF"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# Download
$BinaryPath = "$InstallDir\atf.exe"
Write-Host "Downloading $BinaryName..." -ForegroundColor Cyan

try {
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $BinaryPath
    Write-Host "✓ Downloaded successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Download failed: $_" -ForegroundColor Red
    exit 1
}

# Add to PATH
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable(
        "Path",
        "$CurrentPath;$InstallDir",
        "User"
    )
    Write-Host "✓ Added to PATH" -ForegroundColor Green
} else {
    Write-Host "✓ Already in PATH" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✓ Installation complete!" -ForegroundColor Green
Write-Host "  Binary installed to: $BinaryPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Please restart your terminal and try:" -ForegroundColor Yellow
Write-Host "  atf --help" -ForegroundColor Cyan
