#!/bin/bash
# Build ATF Tools macOS Package (.pkg)

set -e

VERSION=${1:-1.0.0}
BINARY_AMD64="../../dist/atf-darwin-amd64"
BINARY_ARM64="../../dist/atf-darwin-arm64"

echo "Building ATF Tools macOS Package v$VERSION"

# Check binaries exist
if [ ! -f "$BINARY_AMD64" ]; then
    echo "Error: Intel binary not found at $BINARY_AMD64"
    exit 1
fi

if [ ! -f "$BINARY_ARM64" ]; then
    echo "Error: ARM64 binary not found at $BINARY_ARM64"
    exit 1
fi

# Create universal binary using lipo
echo "Creating universal binary..."
lipo -create "$BINARY_AMD64" "$BINARY_ARM64" -output atf

# Verify
lipo -info atf

# Create package structure
echo "Creating package structure..."
rm -rf package-root
mkdir -p package-root/usr/local/bin
mkdir -p package-root/usr/local/share/doc/atf

# Copy binary
cp atf package-root/usr/local/bin/
chmod +x package-root/usr/local/bin/atf

# Create documentation
cat > package-root/usr/local/share/doc/atf/README.txt <<EOF
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
EOF

# Copy license if exists
if [ -f "../../LICENSE" ]; then
    cp ../../LICENSE package-root/usr/local/share/doc/atf/LICENSE.txt
fi

# Build package
echo "Building package..."
pkgbuild --root package-root \
         --identifier com.atf.tools \
         --version "$VERSION" \
         --install-location / \
         --scripts scripts \
         "ATF-Tools-$VERSION.pkg"

# Create distribution package (for better UI)
echo "Creating distribution package..."

cat > distribution.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>ATF Tools</title>
    <organization>com.atf</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="false" hostArchitectures="x86_64,arm64"/>
    
    <welcome file="welcome.html"/>
    <license file="license.html"/>
    <conclusion file="conclusion.html"/>
    
    <pkg-ref id="com.atf.tools"/>
    
    <options customize="never" require-scripts="false"/>
    
    <choices-outline>
        <line choice="default">
            <line choice="com.atf.tools"/>
        </line>
    </choices-outline>
    
    <choice id="default"/>
    
    <choice id="com.atf.tools" visible="false">
        <pkg-ref id="com.atf.tools"/>
    </choice>
    
    <pkg-ref id="com.atf.tools" version="$VERSION" onConclusion="none">ATF-Tools-$VERSION.pkg</pkg-ref>
</installer-gui-script>
EOF

# Create welcome message
cat > welcome.html <<EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, sans-serif; font-size: 13px; }
        h1 { font-size: 18px; }
    </style>
</head>
<body>
    <h1>Welcome to ATF Tools</h1>
    <p>This installer will install ATF Tools v$VERSION on your computer.</p>
    <p>ATF (Agent Traversable File) is a self-indexing document format designed for AI agents.</p>
    <p><strong>Installation location:</strong> /usr/local/bin/atf</p>
    <p><strong>Note:</strong> /usr/local/bin is already in your PATH, so you can use the <code>atf</code> command immediately after installation.</p>
</body>
</html>
EOF

# Create license
cat > license.html <<EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: monospace; font-size: 11px; }
    </style>
</head>
<body>
<pre>
MIT License

Copyright (c) 2025 ATF Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
</pre>
</body>
</html>
EOF

# Create conclusion
cat > conclusion.html <<EOF
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, sans-serif; font-size: 13px; }
        h1 { font-size: 18px; }
        code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Installation Complete!</h1>
    <p>ATF Tools has been successfully installed.</p>
    <p><strong>Try it out:</strong></p>
    <p>Open Terminal and type:</p>
    <p><code>atf --version</code></p>
    <p><code>atf --help</code></p>
    <br>
    <p><strong>Quick Start:</strong></p>
    <ol>
        <li>Create a .atf file</li>
        <li>Run: <code>atf rebuild yourfile.atf</code></li>
        <li>See the auto-generated index!</li>
    </ol>
    <p>Documentation: <a href="https://github.com/atf-tools/atf">https://github.com/atf-tools/atf</a></p>
</body>
</html>
EOF

# Create distribution package
productbuild --distribution distribution.xml \
             --resources . \
             "ATF-Tools-$VERSION-Installer.pkg"

# Cleanup
echo "Cleaning up..."
rm -rf package-root distribution.xml welcome.html license.html conclusion.html atf

echo ""
echo "✓ Package created: ATF-Tools-$VERSION-Installer.pkg"
echo ""
echo "Test it:"
echo "  sudo installer -pkg ATF-Tools-$VERSION-Installer.pkg -target /"
echo ""
echo "Or double-click the .pkg file to install with GUI"
