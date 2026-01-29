# Build IATF Tools MSI Installer
# Requirements: WiX Toolset v3.11+ installed

param(
    [string]$Version = $null,
    [string]$BinaryPath = "..\..\dist\iatf-windows-amd64.exe"
)

# Auto-detect version from VERSION file if not provided
if (-not $Version) {
    $VersionFile = "..\..\VERSION"
    if (Test-Path $VersionFile) {
        $Version = (Get-Content $VersionFile -Raw).Trim()
        Write-Host "Auto-detected version from VERSION file: $Version" -ForegroundColor Green
    } else {
        $Version = "1.0.0"
        Write-Host "VERSION file not found, using default: $Version" -ForegroundColor Yellow
    }
}

Write-Host "Building IATF Tools MSI Installer v$Version" -ForegroundColor Green

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Create temporary build directory
$BuildDir = "$ScriptDir\build"
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

# Copy binary to build directory with standard name
Write-Host "Copying binary..." -ForegroundColor Cyan
if (-not (Test-Path $BinaryPath)) {
    # Try alternative paths
    $AltPaths = @(
        "..\..\iatf.exe",
        "..\..\go\iatf.exe",
        "$env:GOPATH\bin\iatf.exe"
    )
    foreach ($path in $AltPaths) {
        if (Test-Path $path) {
            $BinaryPath = $path
            break
        }
    }
}

if (-not (Test-Path $BinaryPath)) {
    Write-Host "Error: Binary not found at $BinaryPath" -ForegroundColor Red
    Write-Host "Please build the binary first: go build -o iatf.exe ./go" -ForegroundColor Yellow
    exit 1
}

Copy-Item $BinaryPath "$BuildDir\iatf.exe" -Force

# Generate README.txt from README.md
Write-Host "Generating README.txt..." -ForegroundColor Cyan
$ReadmePath = "..\..\README.md"
if (Test-Path $ReadmePath) {
    $ReadmeContent = Get-Content $ReadmePath -Raw
    # Simple conversion - just save as text
    $ReadmeContent | Out-File "$BuildDir\README.txt" -Encoding UTF8
} else {
    @"
IATF Tools - Indexed Agent Traversable File

A file format designed for AI agents to efficiently navigate large documents.

For more information, visit: https://github.com/Winds-AI/agent-traversal-file

Quick Start:
  iatf --help              Show help
  iatf validate file.iatf  Validate an IATF file
  iatf rebuild file.iatf   Rebuild index for an IATF file
  iatf read file.iatf      Read an IATF file

Version: $Version
"@ | Out-File "$BuildDir\README.txt" -Encoding UTF8
}

# Copy LICENSE.txt
Write-Host "Copying LICENSE.txt..." -ForegroundColor Cyan
$LicensePath = "..\..\LICENSE"
if (Test-Path $LicensePath) {
    Copy-Item $LicensePath "$BuildDir\LICENSE.txt" -Force
} else {
    "MIT License - See https://opensource.org/licenses/MIT" | Out-File "$BuildDir\LICENSE.txt" -Encoding UTF8
}

# Generate License.rtf from LICENSE
Write-Host "Generating License.rtf..." -ForegroundColor Cyan
$LicenseContent = Get-Content "$BuildDir\LICENSE.txt" -Raw
$RtfContent = @"
{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}}
\f0\fs24
$($LicenseContent -replace "\n", "\par\n" -replace "\\", "\\\\")
}
"@
$RtfContent | Out-File "$BuildDir\License.rtf" -Encoding UTF8

# Check WiX is installed
$wixPathCandidates = @(
    $env:WIX_PATH,
    $env:WIX,
    "$env:ProgramData\chocolatey\lib\wixtoolset\tools\bin",
    "${env:ProgramFiles(x86)}\WiX Toolset v3.14\bin",
    "${env:ProgramFiles(x86)}\WiX Toolset v3.11\bin",
    "${env:ProgramFiles(x86)}\WiX Toolset v3.10\bin",
    "${env:ProgramFiles(x86)}\WiX Toolset v3.9\bin",
    "${env:ProgramFiles(x86)}\WiX Toolset v3.8\bin"
) | Where-Object { $_ -and $_.Trim().Length -gt 0 }

$wixPath = $null
foreach ($candidate in $wixPathCandidates) {
    if (Test-Path (Join-Path $candidate "candle.exe")) {
        $wixPath = $candidate
        break
    }
}

if (-not $wixPath) {
    $candleCmd = Get-Command candle.exe -ErrorAction SilentlyContinue
    if ($candleCmd) {
        $wixPath = Split-Path $candleCmd.Source -Parent
    }
}

if (-not $wixPath) {
    Write-Host "Error: WiX Toolset not found!" -ForegroundColor Red
    Write-Host "Download from: https://wixtoolset.org/ or set WIX_PATH" -ForegroundColor Yellow
    Write-Host "Or install via Chocolatey: choco install wixtoolset" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found WiX at: $wixPath" -ForegroundColor Green

# Add WiX to PATH temporarily
$env:PATH = "$wixPath;$env:PATH"

# Copy .wxs file to build directory and update version
$WxsSource = "$ScriptDir\iatf.wxs"
$WxsBuild = "$BuildDir\iatf.wxs"

if (-not (Test-Path $WxsSource)) {
    Write-Host "Error: iatf.wxs not found at $WxsSource" -ForegroundColor Red
    exit 1
}

# Read and modify the .wxs to inject version
$WxsContent = Get-Content $WxsSource -Raw
# Replace the version variable definition
$WxsContent = $WxsContent -replace '\$\(var\.ProductVersion\)', $Version
$WxsContent | Out-File $WxsBuild -Encoding UTF8

# Build the MSI
Write-Host "Compiling WiX source..." -ForegroundColor Cyan
Set-Location $BuildDir

$candleResult = & candle.exe -nologo -arch x64 "iatf.wxs" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: candle.exe failed" -ForegroundColor Red
    Write-Host $candleResult -ForegroundColor Red
    exit 1
}

Write-Host "Linking MSI..." -ForegroundColor Cyan
$MsiName = "iatf-tools-$Version.msi"
$lightResult = & light.exe -nologo -ext WixUIExtension -out $MsiName "iatf.wixobj" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: light.exe failed" -ForegroundColor Red
    Write-Host $lightResult -ForegroundColor Red
    exit 1
}

# Move MSI to output directory
$OutputDir = "$ScriptDir\..\..\dist"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$OutputPath = "$OutputDir\$MsiName"
Move-Item "$BuildDir\$MsiName" $OutputPath -Force

# Cleanup build directory
Remove-Item $BuildDir -Recurse -Force

Write-Host "`n✓ Build successful!" -ForegroundColor Green
Write-Host "  Output: $OutputPath" -ForegroundColor Cyan
Write-Host "`nTo install, run: msiexec /i `"$OutputPath`"" -ForegroundColor Yellow
