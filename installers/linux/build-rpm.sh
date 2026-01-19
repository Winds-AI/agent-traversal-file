#!/bin/bash
# Build ATF Tools RPM Package (.rpm) for Fedora/RHEL/CentOS

set -e

VERSION=${1:-1.0.0}
BINARY_AMD64="../../dist/atf-linux-amd64"
BINARY_ARM64="../../dist/atf-linux-arm64"

echo "Building ATF Tools RPM Packages v$VERSION"

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
    
    echo ""
    echo "Building RPM for $ARCH..."
    
    # Check binary exists
    if [ ! -f "$BINARY" ]; then
        echo "Warning: Binary not found at $BINARY, skipping $ARCH"
        return
    fi
    
    # Create RPM build structure
    mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
    
    # Create spec file
    cat > ~/rpmbuild/SPECS/atf-tools.spec <<EOF
Name:           atf-tools
Version:        $VERSION
Release:        1%{?dist}
Summary:        Agent Traversable File - Self-indexing documents for AI agents

License:        MIT
URL:            https://github.com/atf-tools/atf
Source0:        atf

BuildArch:      $ARCH
Requires:       bash

%description
ATF Tools provides commands to create and manage ATF (Agent Traversable File)
documents. ATF is a file format designed for AI agents to efficiently
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
mkdir -p \$RPM_BUILD_ROOT/usr/share/doc/atf-tools
mkdir -p \$RPM_BUILD_ROOT/usr/share/man/man1

# Install binary
install -m 755 %{SOURCE0} \$RPM_BUILD_ROOT/usr/bin/atf

# Install documentation
cat > \$RPM_BUILD_ROOT/usr/share/doc/atf-tools/README <<DOCEOF
ATF Tools v$VERSION

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
DOCEOF

# Install man page
cat > \$RPM_BUILD_ROOT/usr/share/man/man1/atf.1 <<'MANEOF'
.TH ATF 1 "January 2025" "ATF Tools $VERSION" "User Commands"
.SH NAME
atf \- Agent Traversable File document manager
.SH SYNOPSIS
.B atf
.I command
[\fIoptions\fR] [\fIfile\fR]
.SH DESCRIPTION
ATF Tools manages ATF (Agent Traversable File) documents. ATF is a file format
designed for AI agents to efficiently navigate large documents.
.SH COMMANDS
.TP
.B rebuild \fIfile\fR
Rebuild the index for a single ATF file
.TP
.B rebuild-all [\fIdir\fR]
Rebuild all .atf files in directory
.TP
.B watch \fIfile\fR
Watch file and auto-rebuild index when it changes
.TP
.B unwatch \fIfile\fR
Stop watching a file
.TP
.B validate \fIfile\fR
Validate ATF file structure
.SH EXAMPLES
Rebuild: atf rebuild document.atf
.br
Watch: atf watch api-reference.atf
.SH SEE ALSO
Documentation: https://github.com/atf-tools/atf
MANEOF

gzip -9 \$RPM_BUILD_ROOT/usr/share/man/man1/atf.1

%files
%defattr(-,root,root,-)
/usr/bin/atf
/usr/share/doc/atf-tools/README
/usr/share/man/man1/atf.1.gz

%post
# Verify installation
if [ -x "/usr/bin/atf" ]; then
    echo "ATF Tools installed successfully"
    /usr/bin/atf --version || true
fi

%preun
# Stop any running watch processes
if command -v atf >/dev/null 2>&1; then
    WATCH_FILE="\$HOME/.atf/watch.json"
    if [ -f "\$WATCH_FILE" ]; then
        rm -f "\$WATCH_FILE" || true
    fi
fi

%changelog
* $(date '+%a %b %d %Y') ATF Project <atf@example.com> - $VERSION-1
- Initial release
EOF
    
    # Copy binary to SOURCES
    cp "$BINARY" ~/rpmbuild/SOURCES/atf
    
    # Build RPM
    rpmbuild -bb ~/rpmbuild/SPECS/atf-tools.spec --target "$ARCH"
    
    # Copy RPM to current directory
    cp ~/rpmbuild/RPMS/$ARCH/atf-tools-${VERSION}-1.*.${ARCH}.rpm .
    
    echo "✓ Created: atf-tools-${VERSION}-1.*.${ARCH}.rpm"
}

# Build for both architectures
build_rpm "x86_64" "$BINARY_AMD64"
build_rpm "aarch64" "$BINARY_ARM64"

echo ""
echo "✓ RPM packages created"
echo ""
echo "Test installation:"
echo "  sudo rpm -i atf-tools-${VERSION}-1.*.x86_64.rpm"
echo ""
echo "Or:"
echo "  sudo dnf install ./atf-tools-${VERSION}-1.*.x86_64.rpm"
