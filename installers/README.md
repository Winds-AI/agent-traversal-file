# Building Installers

This directory contains scripts to build professional installers for all platforms.

---

## Overview

| Platform | Installer Type | Auto-adds to PATH | Build Platform |
|----------|----------------|-------------------|----------------|
| **Windows** | `.msi` | ✅ Yes (system-wide) | Windows or GitHub Actions |
| **macOS** | `.pkg` | ✅ Yes (/usr/local/bin) | macOS or GitHub Actions |
| **Linux (Debian)** | `.deb` | ✅ Yes (/usr/bin) | Linux or GitHub Actions |
| **Linux (Fedora)** | `.rpm` | ✅ Yes (/usr/bin) | Linux or GitHub Actions |

---

## Automatic Building (Recommended)

**GitHub Actions builds everything automatically when you create a release tag:**

```bash
git tag v1.0.0
git push origin v1.0.0

# GitHub Actions will:
# 1. Build binaries for all platforms
# 2. Create Windows MSI installer
# 3. Create macOS PKG installer
# 4. Create Linux DEB packages (amd64, arm64)
# 5. Create Linux RPM packages (x86_64, aarch64)
# 6. Publish all to GitHub Releases
```

Check the **Actions** tab on GitHub to watch the build progress.

---

## Manual Building

### Prerequisites by Platform

**Windows (for .msi):**
- WiX Toolset v3.11+: https://wixtoolset.org/
- PowerShell

**macOS (for .pkg):**
- Xcode Command Line Tools: `xcode-select --install`
- Both Intel and ARM binaries

**Linux (for .deb/.rpm):**
- dpkg tools: `sudo apt install dpkg-dev` (for .deb)
- rpm-build: `sudo dnf install rpm-build` (for .rpm)

---

## Building Windows MSI

### On Windows:

```powershell
# 1. Install WiX Toolset from https://wixtoolset.org/

# 2. Build Go binaries first
cd go
go build -o ../dist/atf-windows-amd64.exe main.go

# 3. Build installer
cd ../installers/windows
powershell -ExecutionPolicy Bypass -File build-msi.ps1

# Output: ATF-Tools-1.0.0.msi
```

### Features:
- ✅ Installs to `C:\Program Files\ATF Tools\`
- ✅ Adds to system PATH automatically
- ✅ Creates Start Menu shortcuts
- ✅ Includes uninstaller
- ✅ Shows in "Add/Remove Programs"

### Test Installation:
```powershell
# Install
msiexec /i ATF-Tools-1.0.0.msi

# Verify
atf --version

# Uninstall
msiexec /x ATF-Tools-1.0.0.msi
```

---

## Building macOS PKG

### On macOS:

```bash
# 1. Build Go binaries first
cd go
GOOS=darwin GOARCH=amd64 go build -o ../dist/atf-darwin-amd64 main.go
GOOS=darwin GOARCH=arm64 go build -o ../dist/atf-darwin-arm64 main.go

# 2. Build installer
cd ../installers/macos
chmod +x build-pkg.sh scripts/postinstall
./build-pkg.sh

# Output: ATF-Tools-1.0.0-Installer.pkg
```

### Features:
- ✅ Creates universal binary (Intel + Apple Silicon)
- ✅ Installs to `/usr/local/bin/atf`
- ✅ `/usr/local/bin` already in PATH
- ✅ Includes welcome and conclusion screens
- ✅ Shows license agreement

### Test Installation:
```bash
# Install (GUI)
open ATF-Tools-1.0.0-Installer.pkg

# Or install (command line)
sudo installer -pkg ATF-Tools-1.0.0-Installer.pkg -target /

# Verify
atf --version
```

---

## Building Linux DEB

### On Ubuntu/Debian:

```bash
# 1. Build Go binaries first
cd go
GOOS=linux GOARCH=amd64 go build -o ../dist/atf-linux-amd64 main.go
GOOS=linux GOARCH=arm64 go build -o ../dist/atf-linux-arm64 main.go

# 2. Build packages
cd ../installers/linux
chmod +x build-deb.sh
./build-deb.sh

# Output:
#   atf-tools_1.0.0_amd64.deb
#   atf-tools_1.0.0_arm64.deb
```

### Features:
- ✅ Installs to `/usr/bin/atf`
- ✅ Automatically in PATH
- ✅ Includes man page: `man atf`
- ✅ Post-install verification
- ✅ Clean removal support

### Test Installation:
```bash
# Install
sudo dpkg -i atf-tools_1.0.0_amd64.deb

# Or
sudo apt install ./atf-tools_1.0.0_amd64.deb

# Verify
atf --version
man atf

# Uninstall
sudo apt remove atf-tools
```

---

## Building Linux RPM

### On Fedora/RHEL/CentOS:

```bash
# 1. Install rpm-build
sudo dnf install rpm-build

# 2. Build Go binaries first
cd go
GOOS=linux GOARCH=amd64 go build -o ../dist/atf-linux-amd64 main.go
GOOS=linux GOARCH=arm64 go build -o ../dist/atf-linux-arm64 main.go

# 3. Build packages
cd ../installers/linux
chmod +x build-rpm.sh
./build-rpm.sh

# Output:
#   atf-tools-1.0.0-1.*.x86_64.rpm
#   atf-tools-1.0.0-1.*.aarch64.rpm
```

### Features:
- ✅ Installs to `/usr/bin/atf`
- ✅ Automatically in PATH
- ✅ Includes man page
- ✅ Post-install verification
- ✅ Clean removal support

### Test Installation:
```bash
# Install
sudo rpm -i atf-tools-1.0.0-1.*.x86_64.rpm

# Or
sudo dnf install ./atf-tools-1.0.0-1.*.x86_64.rpm

# Verify
atf --version
man atf

# Uninstall
sudo dnf remove atf-tools
```

---

## Distribution Checklist

Before distributing installers, verify:

- [ ] Version number is correct in all files
- [ ] LICENSE file is included
- [ ] README/documentation is included
- [ ] Man pages are generated (Linux)
- [ ] Installers are signed (optional but recommended)
- [ ] Test installation on clean VM
- [ ] Test uninstallation
- [ ] Verify PATH is updated correctly
- [ ] Check installer file sizes are reasonable

---

## File Sizes (Approximate)

| File | Size |
|------|------|
| Binary (compressed) | ~2-5 MB |
| .msi (Windows) | ~3-6 MB |
| .pkg (macOS) | ~5-8 MB |
| .deb (Linux) | ~2-5 MB |
| .rpm (Linux) | ~2-5 MB |

---

## Signing Installers (Optional but Recommended)

### Windows Code Signing:
```powershell
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com ATF-Tools-1.0.0.msi
```

### macOS Code Signing:
```bash
codesign --sign "Developer ID Application: Your Name" ATF-Tools-1.0.0-Installer.pkg
```

### Linux:
- DEB: Use `debsigs` to sign packages
- RPM: Use `rpm --addsign` with GPG key

---

## Troubleshooting

### Windows: "WiX Toolset not found"
**Solution:** Download and install from https://wixtoolset.org/

### macOS: "lipo: can't open input file"
**Solution:** Make sure both Intel and ARM64 binaries are built first

### Linux: "dpkg-deb: command not found"
**Solution:** `sudo apt install dpkg-dev`

### Linux: "rpmbuild: command not found"
**Solution:** `sudo dnf install rpm-build`

### All: "Permission denied"
**Solution:** Make scripts executable: `chmod +x *.sh`

---

## GitHub Actions Integration

The `.github/workflows/release-with-installers.yml` workflow automatically:

1. Builds binaries for all platforms
2. Creates all installers
3. Uploads to GitHub Releases

**No manual building needed** when using GitHub Actions!

---

## Support

For issues with installers:
- Open an issue: https://github.com/atf-tools/atf/issues
- Tag with `installer` label
