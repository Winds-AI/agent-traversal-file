# Build ATF Tools MSI Installer
# Requirements: WiX Toolset v3.11+ installed

param(
    [string]$Version = "1.0.0",
    [string]$BinaryPath = "..\..\dist\atf-windows-amd64.exe"
)

Write-Host "Building ATF Tools MSI Installer v$Version" -ForegroundColor Green

# Check WiX is installed
$wixPath = "${env:ProgramFiles(x86)}\WiX Toolset v3.11\bin"
if (-not (Test-Path "$wixPath\candle.exe")) {
    Write-Host "Error: WiX Toolset not found!" -ForegroundColor Red
    Write-Host "Download from: https://wixtoolset.org/" -ForegroundColor Yellow
    exit 1
}

# Add WiX to PATH temporarily
$env:PATH = "$wixPath;$env:PATH"

# Check binary exists
if (-not (Test-Path $BinaryPath)) {
    Write-Host "Error: Binary not found at $BinaryPath" -ForegroundColor Red
    exit 1
}

# Copy binary to installer directory
Write-Host "Copying binary..." -ForegroundColor Cyan
Copy-Item $BinaryPath "atf.exe" -Force

# Create README.txt
Write-Host "Creating documentation..." -ForegroundColor Cyan
$readme = @"
ATF Tools v$Version

Agent Traversable File - Self-indexing documents for AI agents

USAGE:
  atf rebuild <file>              Rebuild index for a file
  atf rebuild-all [directory]     Rebuild all .atf files
  atf watch <file>                Watch and auto-rebuild
  atf unwatch <file>              Stop watching
  atf validate <file>             Validate file

EXAMPLES:
  atf rebuild document.atf
  atf rebuild-all ./docs
  atf watch api-reference.atf

DOCUMENTATION:
  https://github.com/atf-tools/atf

LICENSE: MIT
"@
$readme | Out-File -FilePath "README.txt" -Encoding utf8

# Create LICENSE.txt
Copy-Item "..\..\LICENSE" "LICENSE.txt" -ErrorAction SilentlyContinue

# Create License.rtf for installer
Write-Host "Creating license RTF..." -ForegroundColor Cyan
$licenseRtf = @"
{\rtf1\ansi\deff0
{\fonttbl{\f0\fswiss Arial;}}
{\colortbl;\red0\green0\blue0;}
\f0\fs20
MIT License\par
\par
Copyright (c) 2025 ATF Project\par
\par
Permission is hereby granted, free of charge, to any person obtaining a copy\par
of this software and associated documentation files (the "Software"), to deal\par
in the Software without restriction, including without limitation the rights\par
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\par
copies of the Software, and to permit persons to whom the Software is\par
furnished to do so, subject to the following conditions:\par
\par
The above copyright notice and this permission notice shall be included in all\par
copies or substantial portions of the Software.\par
\par
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\par
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\par
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\par
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\par
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\par
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\par
SOFTWARE.\par
}
"@
$licenseRtf | Out-File -FilePath "License.rtf" -Encoding ascii

# Update version in WXS file
Write-Host "Updating version in WXS..." -ForegroundColor Cyan
$wxsContent = Get-Content "atf.wxs" -Raw
$wxsContent = $wxsContent -replace 'Version="[\d\.]+"', "Version=`"$Version`""
$wxsContent | Out-File "atf-versioned.wxs" -Encoding utf8

# Build installer
Write-Host "Running candle.exe..." -ForegroundColor Cyan
& candle.exe atf-versioned.wxs -out atf.wixobj
if ($LASTEXITCODE -ne 0) {
    Write-Host "Candle failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Running light.exe..." -ForegroundColor Cyan
& light.exe -ext WixUIExtension -out "ATF-Tools-$Version.msi" atf.wixobj
if ($LASTEXITCODE -ne 0) {
    Write-Host "Light failed!" -ForegroundColor Red
    exit 1
}

# Cleanup
Write-Host "Cleaning up..." -ForegroundColor Cyan
Remove-Item "atf.exe", "atf.wixobj", "atf-versioned.wxs", "ATF-Tools-$Version.wixpdb" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "✓ Installer created: ATF-Tools-$Version.msi" -ForegroundColor Green
Write-Host ""
Write-Host "Test it:" -ForegroundColor Yellow
Write-Host "  msiexec /i ATF-Tools-$Version.msi" -ForegroundColor Cyan
