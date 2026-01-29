# IATF Installation Script for Windows
# Usage: irm https://raw.githubusercontent.com/USER/REPO/main/installers/install.ps1 | iex

param(
    [string]$Version = "",
    [string]$InstallDir = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Configuration
$RepoOwner = if ($env:IATF_REPO_OWNER) { $env:IATF_REPO_OWNER } else { "Winds-AI" }
$RepoName = if ($env:IATF_REPO_NAME) { $env:IATF_REPO_NAME } else { "agent-traversal-file" }
$GitHubRepo = "$RepoOwner/$RepoName"

# Detect if running as Administrator
$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# Set default install directory
if (-not $InstallDir) {
    if ($IsAdmin) {
        $InstallDir = "$env:ProgramFiles\IATF"
    } else {
        $InstallDir = "$env:USERPROFILE\bin"
    }
}

# Helper functions
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Info {
    param([string]$Message)
    Write-ColorOutput "==> $Message" "Green"
}

function Write-Warn {
    param([string]$Message)
    Write-ColorOutput "Warning: $Message" "Yellow"
}

function Write-Err {
    param([string]$Message)
    Write-ColorOutput "Error: $Message" "Red"
}

# Detect architecture
function Get-Architecture {
    $arch = $env:PROCESSOR_ARCHITECTURE
    switch ($arch) {
        "AMD64" { return "amd64" }
        "ARM64" { return "arm64" }
        default {
            Write-Err "Unsupported architecture: $arch"
            exit 1
        }
    }
}

# Get latest release version
function Get-LatestVersion {
    try {
        $apiUrl = "https://api.github.com/repos/$GitHubRepo/releases/latest"
        $response = Invoke-RestMethod -Uri $apiUrl -Method Get -ErrorAction Stop
        return $response.tag_name
    } catch {
        Write-Err "Failed to get latest version: $_"
        exit 1
    }
}

# Download file
function Download-File {
    param(
        [string]$Url,
        [string]$Output
    )

    try {
        Write-Info "Downloading from $Url..."
        Invoke-WebRequest -Uri $Url -OutFile $Output -ErrorAction Stop
    } catch {
        Write-Err "Failed to download file: $_"
        exit 1
    }
}

# Verify checksum
function Verify-Checksum {
    param(
        [string]$FilePath,
        [string]$ChecksumsFile,
        [string]$BinaryName
    )

    try {
        $checksums = Get-Content $ChecksumsFile
        $expectedLine = $checksums | Where-Object { $_ -match $BinaryName } | Select-Object -First 1

        if (-not $expectedLine) {
            Write-Warn "No checksum found for $BinaryName, skipping verification"
            return
        }

        $expectedHash = ($expectedLine -split '\s+')[0]
        $actualHash = (Get-FileHash -Path $FilePath -Algorithm SHA256).Hash.ToLower()

        if ($expectedHash -ne $actualHash) {
            Write-Err "Checksum verification failed!"
            Write-Err "Expected: $expectedHash"
            Write-Err "Got: $actualHash"
            exit 1
        }

        Write-Info "Checksum verified successfully"
    } catch {
        Write-Warn "Failed to verify checksum: $_"
    }
}

# Add to PATH
function Add-ToPath {
    param([string]$Directory)

    # Determine scope
    $scope = if ($IsAdmin) { "Machine" } else { "User" }

    # Get current PATH
    $currentPath = [Environment]::GetEnvironmentVariable("Path", $scope)

    # Check if already in PATH
    if ($currentPath -split ';' | Where-Object { $_ -eq $Directory }) {
        Write-Info "Directory already in PATH"
        return
    }

    # Add to PATH
    try {
        $newPath = "$currentPath;$Directory"
        [Environment]::SetEnvironmentVariable("Path", $newPath, $scope)

        # Update current session
        $env:Path = "$env:Path;$Directory"

        Write-Info "Added $Directory to PATH ($scope)"
    } catch {
        Write-Err "Failed to add to PATH: $_"
        Write-Warn "You may need to manually add $Directory to your PATH"
    }
}

# Main installation
function Main {
    Write-Info "IATF Installation Script"
    Write-Host ""

    # Check admin status
    if ($IsAdmin) {
        Write-Info "Running as Administrator (system-wide install)"
    } else {
        Write-Info "Running as User (user-local install)"
    }

    # Detect architecture
    $arch = Get-Architecture
    Write-Info "Detected Architecture: $arch"
    Write-Info "Install directory: $InstallDir"
    Write-Host ""

    # Get version
    if ($Version) {
        Write-Info "Using specified version: $Version"
    } else {
        Write-Info "Fetching latest version..."
        $Version = Get-LatestVersion
        Write-Info "Latest version: $Version"
    }
    Write-Host ""

    # Construct download URLs
    $binaryName = "iatf-windows-$arch.exe"
    $downloadUrl = "https://github.com/$GitHubRepo/releases/download/$Version/$binaryName"
    $checksumsUrl = "https://github.com/$GitHubRepo/releases/download/$Version/SHA256SUMS"

    # Create temp directory
    $tempDir = Join-Path $env:TEMP "iatf-install-$(Get-Random)"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

    try {
        # Download binary
        $tempBinary = Join-Path $tempDir "iatf.exe"
        Download-File -Url $downloadUrl -Output $tempBinary

        # Download checksums
        $tempChecksums = Join-Path $tempDir "SHA256SUMS"
        Download-File -Url $checksumsUrl -Output $tempChecksums

        # Verify checksum
        Write-Info "Verifying checksum..."
        Verify-Checksum -FilePath $tempBinary -ChecksumsFile $tempChecksums -BinaryName $binaryName
        Write-Host ""

        # Create install directory
        if (-not (Test-Path $InstallDir)) {
            Write-Info "Creating install directory..."
            New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
        }

        # Install binary
        $targetPath = Join-Path $InstallDir "iatf.exe"

        # Check if file exists
        if ((Test-Path $targetPath) -and -not $Force) {
            Write-Warn "IATF is already installed at $targetPath"
            $response = Read-Host "Overwrite? (y/N)"
            if ($response -ne 'y' -and $response -ne 'Y') {
                Write-Info "Installation cancelled"
                return
            }
        }

        Write-Info "Installing IATF to $InstallDir..."
        Copy-Item -Path $tempBinary -Destination $targetPath -Force

        # Add to PATH
        Write-Info "Adding to PATH..."
        Add-ToPath -Directory $InstallDir
        Write-Host ""

        Write-Info "IATF installed successfully!"
        Write-Host ""

        # Verify installation
        Write-Info "Verifying installation..."
        try {
            & $targetPath --version
        } catch {
            Write-Warn "Could not verify installation: $_"
        }

        Write-Host ""
        Write-Info "To get started, run: iatf --help"

        if (-not $IsAdmin) {
            Write-Host ""
            Write-Warn "You may need to restart your terminal for PATH changes to take effect"
        }

    } finally {
        # Cleanup
        if (Test-Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

# Run main function
Main
