# IATF Installation Scripts

This directory contains installation scripts for the IATF CLI tool.

## Quick Install

### Linux/macOS

```bash
curl -fsSL https://raw.githubusercontent.com/chadrwalters/agent-traversal-file/main/installers/install.sh | sudo bash
```

**User-local install (no sudo):**
```bash
curl -fsSL https://raw.githubusercontent.com/chadrwalters/agent-traversal-file/main/installers/install.sh | bash
```

### Windows

```powershell
irm https://raw.githubusercontent.com/chadrwalters/agent-traversal-file/main/installers/install.ps1 | iex
```

**Note:** Run PowerShell as Administrator for system-wide installation.

## Installation Scripts

### `install.sh` (Linux/macOS)

**Features:**
- Auto-detects OS (Linux, macOS/Darwin)
- Auto-detects architecture (amd64, arm64)
- Downloads correct binary from GitHub releases
- Verifies SHA256 checksum
- Installs to `/usr/local/bin/iatf` (with sudo) or `~/.local/bin/iatf` (without sudo)
- Adds `~/.local/bin` to PATH if needed
- Makes binary executable
- Verifies installation

**Environment variables:**
- `IATF_VERSION`: Specify version (default: latest)
- `IATF_INSTALL_DIR`: Override install directory
- `IATF_REPO_OWNER`: Override GitHub repo owner (default: chadrwalters)
- `IATF_REPO_NAME`: Override GitHub repo name (default: agent-traversal-file)

**Example with custom version:**
```bash
IATF_VERSION=v1.0.0 curl -fsSL https://raw.githubusercontent.com/chadrwalters/agent-traversal-file/main/installers/install.sh | sudo bash
```

### `install.ps1` (Windows)

**Features:**
- Auto-detects architecture (AMD64, ARM64)
- Downloads Windows binary from GitHub releases
- Verifies SHA256 checksum
- Installs to `C:\Program Files\IATF` (admin) or `%USERPROFILE%\bin` (user)
- Adds install directory to system PATH permanently
- Verifies installation

**Parameters:**
- `-Version`: Specify version (default: latest)
- `-InstallDir`: Override install directory
- `-Force`: Overwrite existing installation without prompting

**Environment variables:**
- `IATF_REPO_OWNER`: Override GitHub repo owner (default: chadrwalters)
- `IATF_REPO_NAME`: Override GitHub repo name (default: agent-traversal-file)

**Example with custom version:**
```powershell
irm https://raw.githubusercontent.com/chadrwalters/agent-traversal-file/main/installers/install.ps1 | iex -Args "-Version v1.0.0"
```

## Manual Installation

Download the binary for your platform from [GitHub Releases](https://github.com/chadrwalters/agent-traversal-file/releases):

- Windows: `iatf-windows-amd64.exe`
- macOS Intel: `iatf-darwin-amd64`
- macOS Apple Silicon: `iatf-darwin-arm64`
- Linux x86_64: `iatf-linux-amd64`
- Linux ARM64: `iatf-linux-arm64`

Then follow the platform-specific installation instructions in the main [README.md](../README.md#installation).

## Uninstallation

### Linux/macOS

```bash
# System-wide install
sudo rm /usr/local/bin/iatf

# User-local install
rm ~/.local/bin/iatf
```

### Windows

```powershell
# System-wide (PowerShell as Administrator)
Remove-Item "C:\Program Files\IATF\iatf.exe"

# User-local
Remove-Item "$env:USERPROFILE\bin\iatf.exe"
```

Don't forget to remove the directory from your PATH if you manually added it.

## CI/CD Integration

These scripts are used in the GitHub Actions release workflow (`.github/workflows/release.yml`):

1. Workflow builds binaries for all platforms on Linux runner
2. Copies installation scripts to release artifacts
3. Generates SHA256SUMS for all binaries
4. Creates GitHub release with binaries, scripts, and checksums

The workflow uses Go cross-compilation to build all platform binaries from a single Linux runner, eliminating the need for platform-specific build agents.

## Security

- All downloads are verified with SHA256 checksums from the `SHA256SUMS` file in the release
- Scripts only download from official GitHub releases
- No code execution from untrusted sources
- Scripts use HTTPS for all downloads

## Troubleshooting

### "curl: command not found" or "wget: command not found"

Install curl or wget:

```bash
# Debian/Ubuntu
sudo apt-get install curl

# macOS
brew install curl

# Fedora/RHEL
sudo dnf install curl
```

### "Permission denied" on Linux/macOS

Either:
- Run with `sudo` for system-wide installation
- Install to user directory without sudo (script will use `~/.local/bin`)

### "Checksum verification failed"

This usually indicates:
- Network interruption during download
- Release assets were modified (very unlikely)

Try running the installer again. If the problem persists, download the binary manually.

### Windows: "Script execution is disabled"

Enable script execution in PowerShell:

```powershell
# Run as Administrator
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then run the installer again.

## Development

To test the installation scripts locally, you can override the repository and version:

```bash
# Linux/macOS
IATF_REPO_OWNER=yourname IATF_VERSION=v0.0.1-test bash installers/install.sh
```

```powershell
# Windows
$env:IATF_REPO_OWNER="yourname"; .\installers\install.ps1 -Version "v0.0.1-test"
```

## License

MIT License - see [LICENSE](../LICENSE) for details.
