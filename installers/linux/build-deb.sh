#!/bin/bash
# Build IATF Tools Debian Package (.deb)

set -e

VERSION=${1:-1.0.0}
BINARY_AMD64="../../dist/iatf-linux-amd64"
BINARY_ARM64="../../dist/iatf-linux-arm64"

echo "Building IATF Tools Debian Packages v$VERSION"

# Function to build package for an architecture
build_package() {
    local ARCH=$1
    local BINARY=$2
    local PACKAGE_NAME="iatf-tools_${VERSION}_${ARCH}"
    
    echo ""
    echo "Building package for $ARCH..."
    
    # Check binary exists
    if [ ! -f "$BINARY" ]; then
        echo "Warning: Binary not found at $BINARY, skipping $ARCH"
        return
    fi
    
    # Create package structure
    rm -rf "$PACKAGE_NAME"
    mkdir -p "$PACKAGE_NAME/DEBIAN"
    mkdir -p "$PACKAGE_NAME/usr/bin"
    mkdir -p "$PACKAGE_NAME/usr/share/doc/iatf-tools"
    mkdir -p "$PACKAGE_NAME/usr/share/man/man1"
    
    # Copy binary
    cp "$BINARY" "$PACKAGE_NAME/usr/bin/iatf"
    chmod 755 "$PACKAGE_NAME/usr/bin/iatf"
    
    # Create control file
    cat > "$PACKAGE_NAME/DEBIAN/control" <<EOF
Package: iatf-tools
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: IATF Project <IATF@example.com>
Description: Indexed Agent Traversable File - Self-indexing documents for AI agents
 IATF Tools provides commands to create and manage IATF (Indexed Agent Traversable File)
 documents. IATF is a file format designed for AI agents to efficiently
 navigate large documents by loading only relevant sections.
 .
 Features:
  - Auto-generated indexes from content
  - Token-efficient agent navigation
  - Plain text, human-readable format
  - Watch mode for auto-rebuild on save
Homepage: https://github.com/iatf-tools/iatf
EOF
    
    # Create postinst script
    cat > "$PACKAGE_NAME/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e

# Verify installation
if [ -x "/usr/bin/iatf" ]; then
    echo "IATF Tools installed successfully"
    /usr/bin/iatf --version || true
fi

exit 0
EOF
    chmod 755 "$PACKAGE_NAME/DEBIAN/postinst"
    
    # Create prerm script
    cat > "$PACKAGE_NAME/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e

# Stop any running watch processes
if command -v iatf >/dev/null 2>&1; then
    # Stop all watches (best effort)
    WATCH_FILE="$HOME/.iatf/watch.json"
    if [ -f "$WATCH_FILE" ]; then
        rm -f "$WATCH_FILE" || true
    fi
fi

exit 0
EOF
    chmod 755 "$PACKAGE_NAME/DEBIAN/prerm"
    
    # Create documentation
    cat > "$PACKAGE_NAME/usr/share/doc/iatf-tools/README" <<EOF
IATF Tools v$VERSION

Indexed Agent Traversable File - Self-indexing documents for AI agents

USAGE:
  iatf rebuild <file>              Rebuild index for a file
  iatf rebuild-all [directory]     Rebuild all .iatf files
  iatf watch <file>                Watch and auto-rebuild
  iatf unwatch <file>              Stop watching
  iatf validate <file>             Validate file

EXAMPLES:
  iatf rebuild document.iatf
  iatf rebuild-all ./docs
  iatf watch api-reference.iatf

DOCUMENTATION:
  https://github.com/iatf-tools/iatf

LICENSE: MIT
EOF
    
    # Create copyright file
    cat > "$PACKAGE_NAME/usr/share/doc/iatf-tools/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: iatf-tools
Source: https://github.com/iatf-tools/iatf

Files: *
Copyright: 2025 IATF Project
License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a
 copy of this software and associated documentation files (the "Software"),
 to deal in the Software without restriction, including without limitation
 the rights to use, copy, modify, merge, publish, distribute, sublicense,
 and/or sell copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included
 in all copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 DEALINGS IN THE SOFTWARE.
EOF
    
    # Create man page
    cat > "$PACKAGE_NAME/usr/share/man/man1/iatf.1" <<'EOF'
.TH iatf 1 "January 2025" "IATF Tools 1.0.0" "User Commands"
.SH NAME
iatf \\- Indexed Agent Traversable File document manager
.SH SYNOPSIS
.B iatf
.I command
[\fIoptions\fR] [\fIfile\fR]
.SH DESCRIPTION
IATF Tools manages IATF (Indexed Agent Traversable File) documents. IATF is a file format
designed for AI agents to efficiently navigate large documents.
.SH COMMANDS
.TP
.B rebuild \fIfile\fR
Rebuild the index for a single iatf file
.TP
.B rebuild-all [\fIdir\fR]
Rebuild all .iatf files in directory (default: current directory)
.TP
.B watch \fIfile\fR
Watch file and auto-rebuild index when it changes
.TP
.B unwatch \fIfile\fR
Stop watching a file
.TP
.B validate \fIfile\fR
Validate iatf file structure
.TP
.B --help
Display help information
.TP
.B --version
Display version information
.SH EXAMPLES
.TP
Rebuild a single file:
.B iatf rebuild document.iatf
.TP
Rebuild all files in docs directory:
.B iatf rebuild-all ./docs
.TP
Watch a file for changes:
.B iatf watch api-reference.iatf
.SH FILES
.TP
.I ~/.iatf/watch.json
Watch state file (tracks which files are being watched)
.SH AUTHOR
IATF Project
.SH SEE ALSO
Full documentation: <https://github.com/iatf-tools/iatf>
EOF
    
    # Compress man page
    gzip -9 -n "$PACKAGE_NAME/usr/share/man/man1/iatf.1"
    
    # Create changelog
    cat > "$PACKAGE_NAME/usr/share/doc/iatf-tools/changelog.gz" <<EOF
iatf-tools ($VERSION) stable; urgency=medium

  * Initial release

 -- IATF Project <IATF@example.com>  $(date -R)
EOF
    gzip -9 -n "$PACKAGE_NAME/usr/share/doc/iatf-tools/changelog.gz"
    
    # Build package
    dpkg-deb --build "$PACKAGE_NAME"
    
    echo "âœ“ Created: ${PACKAGE_NAME}.deb"
}

# Build for both architectures
build_package "amd64" "$BINARY_AMD64"
build_package "arm64" "$BINARY_ARM64"

echo ""
echo "âœ“ Debian packages created"
echo ""
echo "Test installation:"
echo "  sudo dpkg -i iatf-tools_${VERSION}_amd64.deb"
echo ""
echo "Or:"
echo "  sudo apt install ./iatf-tools_${VERSION}_amd64.deb"









