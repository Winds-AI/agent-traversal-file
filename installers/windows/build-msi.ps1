# Build IATF Tools MSI Installer
# Requirements: WiX Toolset v3.11+ installed

param(
    [string]$Version = "1.0.0",
    [string]$BinaryPath = "..\..\dist\iatf-windows-amd64.exe"
)

Write-Host "Building IATF Tools MSI Installer v$Version" -ForegroundColor Green

# Check WiX is installed
$wixPathCandidates = @(
    $env:WIX_PATH,
    $env:WIX,
    "$env:ProgramData\\chocolatey\\lib\\wixtoolset\\tools\\bin",
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
Copy-Item $BinaryPath "iatf.exe" -Force

# Create README.txt
Write-Host "Creating documentation..." -ForegroundColor Cyan
$readmeLines = @(
    "IATF Tools v$Version",
    "",
    "Indexed Agent Traversable File - Self-indexing documents for AI agents",
    "",
    "USAGE:",
    "  iatf rebuild <file>              Rebuild index for a file",
    "  iatf rebuild-all [directory]     Rebuild all .iatf files",
    "  iatf watch <file>                Watch and auto-rebuild",
    "  iatf unwatch <file>              Stop watching",
    "  iatf validate <file>             Validate file",
    "",
    "EXAMPLES:",
    "  iatf rebuild document.iatf",
    "  iatf rebuild-all ./docs",
    "  iatf watch api-reference.iatf",
    "",
    "DOCUMENTATION:",
    "  https://github.com/iatf-tools/iatf",
    "",
    "LICENSE: MIT"
)
$readmeLines -join "`r`n" | Out-File -FilePath "README.txt" -Encoding utf8

# Create LICENSE.txt
Copy-Item "..\..\LICENSE" "LICENSE.txt" -ErrorAction SilentlyContinue

# Create License.rtf for installer
Write-Host "Creating license RTF..." -ForegroundColor Cyan
$licenseLines = @(
    '{\\rtf1\\ansi\\deff0',
    '{\\fonttbl{\\f0\\fswiss Arial;}}',
    '{\\colortbl;\\red0\\green0\\blue0;}',
    '\\f0\\fs20',
    'MIT License\\par',
    '\\par',
    'Copyright (c) 2025 IATF Project\\par',
    '\\par',
    'Permission is hereby granted, free of charge, to any person obtaining a copy\\par',
    'of this software and associated documentation files (the "Software"), to deal\\par',
    'in the Software without restriction, including without limitation the rights\\par',
    'to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\\par',
    'copies of the Software, and to permit persons to whom the Software is\\par',
    'furnished to do so, subject to the following conditions:\\par',
    '\\par',
    'The above copyright notice and this permission notice shall be included in all\\par',
    'copies or substantial portions of the Software.\\par',
    '\\par',
    'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\\par',
    'IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\\par',
    'FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\\par',
    'AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\\par',
    'LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\\par',
    'OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\\par',
    'SOFTWARE.\\par',
    '}'
)
$licenseLines -join "`r`n" | Out-File -FilePath "License.rtf" -Encoding ascii

# Update version in WXS file
Write-Host "Updating version in WXS..." -ForegroundColor Cyan
$wxsContent = Get-Content "iatf.wxs" -Raw
$wxsContent = $wxsContent -replace 'Version="[\d\.]+"', "Version=`"$Version`""
$wxsContent | Out-File "iatf-versioned.wxs" -Encoding utf8

# Build installer
Write-Host "Running candle.exe..." -ForegroundColor Cyan
& candle.exe iatf-versioned.wxs -out iatf.wixobj
if ($LASTEXITCODE -ne 0) {
    Write-Host "Candle failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Running light.exe..." -ForegroundColor Cyan
& light.exe -ext WixUIExtension -out "iatf-tools-$Version.msi" iatf.wixobj
if ($LASTEXITCODE -ne 0) {
    Write-Host "Light failed!" -ForegroundColor Red
    exit 1
}

# Cleanup
Write-Host "Cleaning up..." -ForegroundColor Cyan
Remove-Item "iatf.exe", "iatf.wixobj", "iatf-versioned.wxs", "iatf-tools-$Version.wixpdb" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Installer created: iatf-tools-$Version.msi" -ForegroundColor Green
Write-Host ""
Write-Host "Test it:" -ForegroundColor Yellow
Write-Host "  msiexec /i iatf-tools-$Version.msi" -ForegroundColor Cyan









