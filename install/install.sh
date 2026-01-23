#!/bin/bash
# IATF Tools Installer for macOS/Linux

set -e

echo "Installing IATF Tools..."

# Detect OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Map architecture names
if [ "$ARCH" = "x86_64" ]; then
    ARCH="amd64"
elif [ "$ARCH" = "aarch64" ]; then
    ARCH="arm64"
fi

# Determine binary name
if [ "$OS" = "darwin" ]; then
    BINARY="iatf-darwin-${ARCH}"
elif [ "$OS" = "linux" ]; then
    BINARY="iatf-linux-${ARCH}"
else
    echo "Error: Unsupported OS: $OS"
    exit 1
fi

# Get latest version
LATEST_URL="https://api.github.com/repos/iatf-tools/iatf/releases/latest"
VERSION=$(curl -s $LATEST_URL | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

if [ -z "$VERSION" ]; then
    echo "Error: Could not determine latest version"
    exit 1
fi

echo "Latest version: $VERSION"

# Download URL
DOWNLOAD_URL="https://github.com/iatf-tools/iatf/releases/download/${VERSION}/${BINARY}"

# Temporary download location
TMP_FILE="/tmp/iatf-${VERSION}"

# Download binary
echo "Downloading ${BINARY}..."
if command -v curl &> /dev/null; then
    curl -L "$DOWNLOAD_URL" -o "$TMP_FILE"
elif command -v wget &> /dev/null; then
    wget "$DOWNLOAD_URL" -O "$TMP_FILE"
else
    echo "Error: Neither curl nor wget found. Please install one of them."
    exit 1
fi

# Make executable
chmod +x "$TMP_FILE"

# Determine installation directory
if [ -w "/usr/local/bin" ]; then
    INSTALL_DIR="/usr/local/bin"
    SUDO=""
elif [ -n "$HOME" ]; then
    INSTALL_DIR="$HOME/.local/bin"
    mkdir -p "$INSTALL_DIR"
    SUDO=""
else
    INSTALL_DIR="/usr/local/bin"
    SUDO="sudo"
fi

# Install
echo "Installing to $INSTALL_DIR..."
$SUDO mv "$TMP_FILE" "$INSTALL_DIR/iatf"

# Add to PATH if needed
if [ "$INSTALL_DIR" = "$HOME/.local/bin" ]; then
    SHELL_CONFIG=""
    
    if [ -f "$HOME/.bashrc" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    elif [ -f "$HOME/.zshrc" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    elif [ -f "$HOME/.profile" ]; then
        SHELL_CONFIG="$HOME/.profile"
    fi
    
    if [ -n "$SHELL_CONFIG" ]; then
        if ! grep -q "$INSTALL_DIR" "$SHELL_CONFIG"; then
            echo "" >> "$SHELL_CONFIG"
            echo "# IATF Tools" >> "$SHELL_CONFIG"
            echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> "$SHELL_CONFIG"
            echo "âœ“ Added to $SHELL_CONFIG"
            echo ""
            echo "Please restart your terminal or run:"
            echo "  source $SHELL_CONFIG"
        fi
    fi
fi

echo ""
echo "âœ“ Installation complete!"
echo "  Binary installed to: $INSTALL_DIR/iatf"
echo ""
echo "Try it out:"
echo "  iatf --help"








