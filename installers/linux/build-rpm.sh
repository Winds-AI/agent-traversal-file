#!/bin/bash
# Build IATF Tools RPM Package (.rpm) for Fedora/RHEL/CentOS

set -e

VERSION=${1:-1.0.0}
BINARY_AMD64="../../dist/iatf-linux-amd64"
BINARY_ARM64="../../dist/iatf-linux-arm64"

echo "Building IATF Tools RPM Packages v$VERSION"

# Check if rpmbuild is installed
if ! command -v rpmbuild &> /dev/null; then
    echo "Error: rpmbuild not found. Install with:"
    echo "  Fedora/RHEL: sudo dnf install rpm-build"
    echo "  Ubuntu/Debian: sudo apt install rpm"
    exit 1
fi

# Function to build RPM for an architecture
build_rpm() {
    local ARCH=$1
    local BINARY=$2
    local HOST_ARCH
    
    echo ""
    echo "Building RPM for $ARCH..."

    HOST_ARCH=$(rpmbuild --eval '%{_host_cpu}' 2>/dev/null || echo "")
    if [ -n "$HOST_ARCH" ] && [ "$ARCH" != "$HOST_ARCH" ]; then
        echo "Warning: Host architecture $HOST_ARCH cannot build $ARCH RPM, skipping"
        return
    fi
    
    # Check binary exists
    if [ ! -f "$BINARY" ]; then
        echo "Warning: Binary not found at $BINARY, skipping $ARCH"
        return
    fi
    
    # Create RPM build structure
    mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
    
    # Create spec file
    cat > ~/rpmbuild/SPECS/iatf-tools.spec <<EOF
Name:           iatf-tools
Version:        $VERSION
Release:        1%{?dist}
Summary:        Indexed Agent Traversable File - Self-indexing documents for AI agents

License:        MIT
URL:            https://github.com/iatf-tools/iatf
Source0:        iatf

BuildArch:      $ARCH
Requires:       bash

%description
IATF Tools provides commands to create and manage IATF (Indexed Agent Traversable File)
documents. IATF is a file format designed for AI agents to efficiently
navigate large documents by loading only relevant sections.

Features:
- Auto-generated indexes from content
- Token-efficient agent navigation
- Plain text, human-readable format
- Watch mode for auto-rebuild on save

%prep
# No prep needed

%build
# No build needed (binary provided)

%install
rm -rf \$RPM_BUILD_ROOT
mkdir -p \$RPM_BUILD_ROOT/usr/bin
mkdir -p \$RPM_BUILD_ROOT/usr/share/doc/iatf-tools
mkdir -p \$RPM_BUILD_ROOT/usr/share/man/man1

# Install binary
install -m 755 %{SOURCE0} \$RPM_BUILD_ROOT/usr/bin/iatf

# Install documentation
cat > \$RPM_BUILD_ROOT/usr/share/doc/iatf-tools/README <<DOCEOF
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
DOCEOF

# Install man page
cat > \$RPM_BUILD_ROOT/usr/share/man/man1/iatf.1 <<'MANEOF'
.TH iatf 1 "January 2025" "IATF Tools $VERSION" "User Commands"
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
Rebuild all .iatf files in directory
.TP
.B watch \fIfile\fR
Watch file and auto-rebuild index when it changes
.TP
.B unwatch \fIfile\fR
Stop watching a file
.TP
.B validate \fIfile\fR
Validate iatf file structure
.SH EXAMPLES
Rebuild: iatf rebuild document.iatf
.br
Watch: iatf watch api-reference.iatf
.SH SEE ALSO
Documentation: https://github.com/iatf-tools/iatf
MANEOF

gzip -9 \$RPM_BUILD_ROOT/usr/share/man/man1/iatf.1

%files
%defattr(-,root,root,-)
/usr/bin/iatf
/usr/share/doc/iatf-tools/README
/usr/share/man/man1/iatf.1.gz

%post
# Verify installation
if [ -x "/usr/bin/iatf" ]; then
    echo "IATF Tools installed successfully"
    /usr/bin/iatf --version || true
fi

%preun
# Stop any running watch processes
if command -v iatf >/dev/null 2>&1; then
    WATCH_FILE="\$HOME/.iatf/watch.json"
    if [ -f "\$WATCH_FILE" ]; then
        rm -f "\$WATCH_FILE" || true
    fi
fi

%changelog
* $(date '+%a %b %d %Y') IATF Project <IATF@example.com> - $VERSION-1
- Initial release
EOF
    
    # Copy binary to SOURCES
    cp "$BINARY" ~/rpmbuild/SOURCES/iatf
    
    # Build RPM
    rpmbuild -bb ~/rpmbuild/SPECS/iatf-tools.spec --target "$ARCH"
    
    # Copy RPM to current directory (dist tag may be empty or include .fcXX)
    rpm_source=$(ls ~/rpmbuild/RPMS/$ARCH/iatf-tools-${VERSION}-1*.${ARCH}.rpm 2>/dev/null | head -n 1)
    if [ -z "$rpm_source" ]; then
        echo "Error: RPM not found for $ARCH"
        return 1
    fi
    cp "$rpm_source" .
    
    echo "âœ“ Created: $(basename "$rpm_source")"
}

# Build for both architectures
build_rpm "x86_64" "$BINARY_AMD64"
build_rpm "aarch64" "$BINARY_ARM64"

echo ""
echo "âœ“ RPM packages created"
echo ""
echo "Test installation:"
echo "  sudo rpm -i iatf-tools-${VERSION}-1.*.x86_64.rpm"
echo ""
echo "Or:"
echo "  sudo dnf install ./iatf-tools-${VERSION}-1.*.x86_64.rpm"









