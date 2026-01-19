# Changelog

All notable changes to ATF Tools will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-01-20

### Added
- Initial release of ATF Tools
- `atf rebuild <file>` - Rebuild index for a single file
- `atf rebuild-all [directory]` - Rebuild all .atf files in directory
- `atf watch <file>` - Watch file and auto-rebuild on changes
- `atf unwatch <file>` - Stop watching a file
- `atf validate <file>` - Validate ATF file structure
- Python implementation (zero dependencies)
- Go implementation (compiles to standalone binaries)
- Windows MSI installer
- macOS PKG installer
- Linux DEB packages (amd64, arm64)
- Linux RPM packages (x86_64, aarch64)
- GitHub Actions workflows for automated builds
- Quick install scripts (install.sh, install.ps1)
- Complete documentation (README, QUICKSTART, SPECIFICATION)
- Example ATF files

### Format Specification
- Header section with metadata (@title, @author, etc.)
- Auto-generated INDEX section
- CONTENT section with sections marked by {#id} tags
- Section metadata: @summary, @created, @modified
- Line-based addressing for agent navigation

[Unreleased]: https://github.com/atf-tools/atf/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/atf-tools/atf/releases/tag/v1.0.0
