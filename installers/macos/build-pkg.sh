#!/bin/bash
# Build IATF Tools macOS Package (.pkg)

set -e

VERSION=${1:-1.0.0}
BINARY_AMD64="../../dist/iatf-darwin-amd64"
BINARY_ARM64="../../dist/iatf-darwin-arm64"

echo "Building IATF Tools macOS Package v$VERSION"

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
lipo -create "$BINARY_AMD64" "$BINARY_ARM64" -output iatf

# Verify
lipo -info iatf

# Create package structure
echo "Creating package structure..."
rm -rf package-root
mkdir -p package-root/usr/local/bin
mkdir -p package-root/usr/local/share/doc/iatf

# Copy binary
cp iatf package-root/usr/local/bin/
chmod +x package-root/usr/local/bin/iatf

# Create documentation
cat > package-root/usr/local/share/doc/iatf/README.txt <<EOF
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

# Copy license if exists
if [ -f "../../LICENSE" ]; then
    cp ../../LICENSE package-root/usr/local/share/doc/iatf/LICENSE.txt
fi

# Build package
echo "Building package..."
pkgbuild --root package-root \
         --identifier com.iatf.tools \
         --version "$VERSION" \
         --install-location / \
         --scripts scripts \
         "iatf-tools-$VERSION.pkg"

# Create distribution package (for better UI)
echo "Creating distribution package..."

cat > distribution.xml <<EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>IATF Tools</title>
    <organization>com.iatf</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="false" hostArchitectures="x86_64,arm64"/>
    
    <welcome file="welcome.html"/>
    <license file="license.html"/>
    <conclusion file="conclusion.html"/>
    
    <pkg-ref id="com.iatf.tools"/>
    
    <options customize="never" require-scripts="false"/>
    
    <choices-outline>
        <line choice="default">
            <line choice="com.iatf.tools"/>
        </line>
    </choices-outline>
    
    <choice id="default"/>
    
    <choice id="com.iatf.tools" visible="false">
        <pkg-ref id="com.iatf.tools"/>
    </choice>
    
    <pkg-ref id="com.iatf.tools" version="$VERSION" onConclusion="none">iatf-tools-$VERSION.pkg</pkg-ref>
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
    <h1>Welcome to IATF Tools</h1>
    <p>This installer will install IATF Tools v$VERSION on your computer.</p>
    <p>IATF (Indexed Agent Traversable File) is a self-indexing document format designed for AI agents.</p>
    <p><strong>Installation location:</strong> /usr/local/bin/iatf</p>
    <p><strong>Note:</strong> /usr/local/bin is already in your PATH, so you can use the <code>iatf</code> command immediately after installation.</p>
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

Copyright (c) 2025 IATF Project

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
    <p>IATF Tools has been successfully installed.</p>
    <p><strong>Try it out:</strong></p>
    <p>Open Terminal and type:</p>
    <p><code>iatf --version</code></p>
    <p><code>iatf --help</code></p>
    <br>
    <p><strong>Quick Start:</strong></p>
    <ol>
        <li>Create a .iatf file</li>
        <li>Run: <code>iatf rebuild yourfile.iatf</code></li>
        <li>See the auto-generated index!</li>
    </ol>
    <p>Documentation: <a href="https://github.com/iatf-tools/iatf">https://github.com/iatf-tools/iatf</a></p>
</body>
</html>
EOF

# Create distribution package
productbuild --distribution distribution.xml \
             --resources . \
             "iatf-tools-$VERSION-Installer.pkg"

# Cleanup
echo "Cleaning up..."
rm -rf package-root distribution.xml welcome.html license.html conclusion.html iatf

echo ""
echo "âœ“ Package created: iatf-tools-$VERSION-Installer.pkg"
echo ""
echo "Test it:"
echo "  sudo installer -pkg iatf-tools-$VERSION-Installer.pkg -target /"
echo ""
echo "Or double-click the .pkg file to install with GUI"









