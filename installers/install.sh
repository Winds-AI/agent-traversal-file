#!/usr/bin/env bash

# IATF Installation Script for Linux/macOS
# Usage: curl -fsSL https://raw.githubusercontent.com/USER/REPO/main/installers/install.sh | sudo bash

set -e

# Configuration
REPO_OWNER="${IATF_REPO_OWNER:-chadrwalters}"
REPO_NAME="${IATF_REPO_NAME:-agent-traversal-file}"
GITHUB_REPO="${REPO_OWNER}/${REPO_NAME}"
INSTALL_DIR="${IATF_INSTALL_DIR:-/usr/local/bin}"
USER_INSTALL_DIR="${HOME}/.local/bin"
USE_SUDO=1

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}==>${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

log_error() {
    echo -e "${RED}Error:${NC} $1" >&2
}

# Detect OS
detect_os() {
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    case "$OS" in
        linux*)
            OS="linux"
            ;;
        darwin*)
            OS="darwin"
            ;;
        *)
            log_error "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    echo "$OS"
}

# Detect architecture
detect_arch() {
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64|amd64)
            ARCH="amd64"
            ;;
        aarch64|arm64)
            ARCH="arm64"
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
    echo "$ARCH"
}

# Get latest release version
get_latest_version() {
    if command -v curl >/dev/null 2>&1; then
        VERSION=$(curl -fsSL "https://api.github.com/repos/${GITHUB_REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    elif command -v wget >/dev/null 2>&1; then
        VERSION=$(wget -qO- "https://api.github.com/repos/${GITHUB_REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    else
        log_error "curl or wget is required"
        exit 1
    fi

    if [ -z "$VERSION" ]; then
        log_error "Failed to get latest version"
        exit 1
    fi

    echo "$VERSION"
}

# Download file
download_file() {
    local url=$1
    local output=$2

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "$output" "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$output" "$url"
    else
        log_error "curl or wget is required"
        exit 1
    fi
}

# Verify checksum
verify_checksum() {
    local file=$1
    local checksums_file=$2
    local binary_name=$3

    if ! command -v sha256sum >/dev/null 2>&1; then
        log_warn "sha256sum not found, skipping checksum verification"
        return 0
    fi

    local expected_checksum=$(grep "$binary_name" "$checksums_file" | awk '{print $1}')
    if [ -z "$expected_checksum" ]; then
        log_warn "No checksum found for $binary_name, skipping verification"
        return 0
    fi

    local actual_checksum=$(sha256sum "$file" | awk '{print $1}')

    if [ "$expected_checksum" != "$actual_checksum" ]; then
        log_error "Checksum verification failed!"
        log_error "Expected: $expected_checksum"
        log_error "Got: $actual_checksum"
        exit 1
    fi

    log_info "Checksum verified successfully"
}

# Check if running with sudo
check_sudo() {
    if [ "$EUID" -eq 0 ]; then
        USE_SUDO=0
        INSTALL_DIR="/usr/local/bin"
    else
        if command -v sudo >/dev/null 2>&1; then
            USE_SUDO=1
            INSTALL_DIR="/usr/local/bin"
        else
            log_warn "sudo not available, installing to user directory"
            USE_SUDO=0
            INSTALL_DIR="$USER_INSTALL_DIR"
        fi
    fi
}

# Main installation
main() {
    log_info "IATF Installation Script"
    echo

    # Detect system
    OS=$(detect_os)
    ARCH=$(detect_arch)
    log_info "Detected OS: $OS"
    log_info "Detected Architecture: $ARCH"

    # Check sudo
    check_sudo
    log_info "Install directory: $INSTALL_DIR"
    echo

    # Get version
    if [ -n "$IATF_VERSION" ]; then
        VERSION="$IATF_VERSION"
        log_info "Using specified version: $VERSION"
    else
        log_info "Fetching latest version..."
        VERSION=$(get_latest_version)
        log_info "Latest version: $VERSION"
    fi
    echo

    # Construct download URLs
    BINARY_NAME="iatf-${OS}-${ARCH}"
    DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/releases/download/${VERSION}/${BINARY_NAME}"
    CHECKSUMS_URL="https://github.com/${GITHUB_REPO}/releases/download/${VERSION}/SHA256SUMS"

    # Create temp directory
    TEMP_DIR=$(mktemp -d)
    trap "rm -rf $TEMP_DIR" EXIT

    log_info "Downloading IATF binary..."
    download_file "$DOWNLOAD_URL" "$TEMP_DIR/iatf"

    log_info "Downloading checksums..."
    download_file "$CHECKSUMS_URL" "$TEMP_DIR/SHA256SUMS"

    # Verify checksum
    log_info "Verifying checksum..."
    verify_checksum "$TEMP_DIR/iatf" "$TEMP_DIR/SHA256SUMS" "$BINARY_NAME"
    echo

    # Make executable
    chmod +x "$TEMP_DIR/iatf"

    # Install
    log_info "Installing IATF to $INSTALL_DIR..."
    if [ $USE_SUDO -eq 1 ] && [ "$EUID" -ne 0 ]; then
        sudo mkdir -p "$INSTALL_DIR"
        sudo cp "$TEMP_DIR/iatf" "$INSTALL_DIR/iatf"
    else
        mkdir -p "$INSTALL_DIR"
        cp "$TEMP_DIR/iatf" "$INSTALL_DIR/iatf"
    fi

    # Add to PATH if user install
    if [ "$INSTALL_DIR" = "$USER_INSTALL_DIR" ]; then
        if [[ ":$PATH:" != *":$USER_INSTALL_DIR:"* ]]; then
            log_info "Adding $USER_INSTALL_DIR to PATH..."

            # Detect shell and update rc file
            SHELL_NAME=$(basename "$SHELL")
            case "$SHELL_NAME" in
                bash)
                    RC_FILE="$HOME/.bashrc"
                    ;;
                zsh)
                    RC_FILE="$HOME/.zshrc"
                    ;;
                *)
                    RC_FILE="$HOME/.profile"
                    ;;
            esac

            echo "" >> "$RC_FILE"
            echo "# Added by IATF installer" >> "$RC_FILE"
            echo "export PATH=\"\$PATH:$USER_INSTALL_DIR\"" >> "$RC_FILE"

            log_warn "Please run: source $RC_FILE"
            log_warn "Or restart your shell to update PATH"
        fi
    fi

    echo
    log_info "IATF installed successfully!"
    echo

    # Verify installation
    if command -v iatf >/dev/null 2>&1; then
        log_info "Verifying installation..."
        iatf --version
    else
        log_warn "iatf command not found in PATH"
        log_warn "You may need to restart your shell or run: export PATH=\"\$PATH:$INSTALL_DIR\""
    fi

    echo
    log_info "To get started, run: iatf --help"
}

main "$@"
