# Repository Guidelines

## Project Structure & Module Organization
- `go/` houses the Go CLI implementation (single binary). Entry point: `go/main.go`.
- `python/` contains the reference Python CLI (`python/iatf.py`).
- `examples/` holds sample `.iatf` files used for quick manual checks.
- `install/` and `installers/` include installer scripts and packaging assets.
- Root docs like `README.md`, `SPECIFICATION.md`, and `CONTRIBUTING.md` define the format and contributor workflow.

## Build, Test, and Development Commands
- Build binary: `go build -o iatf ./go` (run from repository root)
- Run commands: `./iatf rebuild examples/simple.iatf`
- Validate: `./iatf validate examples/simple.iatf`
- Python alternative: `python python/iatf.py rebuild examples/simple.iatf`
- **Note:** All commands above are intended to be run from the repository root directory
- **Windows users:** Use `iatf.exe` instead of `iatf` in commands, and the build command produces `iatf.exe`: `go build -o iatf.exe ./go`

## Installation Scripts
- Linux/macOS: `installers/install.sh` - Auto-detects OS/arch, downloads from GitHub releases, verifies checksums, and installs to `/usr/local/bin` (sudo) or `~/.local/bin` (user)
- Windows: `installers/install.ps1` - PowerShell script that auto-detects architecture, downloads binary, verifies checksums, installs to Program Files (admin) or user directory, and adds to PATH

## CI/CD Pipeline
- Single job workflow: `.github/workflows/release.yml`
- Builds all platform binaries from Linux runner using Go cross-compilation
- Platforms supported: Windows (amd64), macOS (amd64, arm64), Linux (amd64, arm64)
- Cross-compilation: No platform-specific runners needed (builds everything on ubuntu-latest)
- Releases include: binaries, install scripts (install.sh, install.ps1), and SHA256SUMS
- Workflow triggers on version tags (v*) and manual dispatch

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indentation, type hints where helpful, and docstrings for functions.
- Go: `gofmt` formatting, idiomatic names, and comments on exported functions.
- Branch naming follows `feature/your-feature-name`.

## Testing Guidelines
- No dedicated test suite is present yet. Validate changes by running the seven commands (rebuild, rebuild-all, watch, unwatch, validate, index, read) on files in `examples/`.
- Always do manual testing for task requirements in both implementations: build/run/validate with the Go CLI and run the equivalent commands with the Python CLI.
- Go tests are noted as TODO; `go test` should remain clean if added.

## Documentation Guidelines
- Do not repeat information across docs. If something is explained in one place, reference it rather than duplicating.
- Keep docs DRY (Don't Repeat Yourself) - single source of truth for each concept.
- When feature specs or logic change, update relevant documentation to remove outdated behavior and describe the new behavior.

## Commit & Pull Request Guidelines
- Auto commits and PR's NOT ALLOWED.

## Security & Configuration Notes
- Python watch state is stored in `~/.iatf/watch.json`; avoid committing user-specific state.
- Install scripts automatically verify SHA256 checksums from releases for security
- Install scripts handle both privileged (sudo/admin) and unprivileged installations

## Problem Statement
IATF exists to make large documents navigable for AI agents without loading entire files or wasting tokens. Instead of requiring RAG-style pipelines, the format works with simple grep-like tools as models get smarter about retrieval. IATF files can define the full scope of work (requirements, flows, test cases, and expected outcomes) in single file for small hobby projects and divided in multiple IATF files for larger projects so agents can look up the exact section they need via the INDEX and act on it quickly.





