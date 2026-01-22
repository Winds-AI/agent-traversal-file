# Repository Guidelines

## Project Structure & Module Organization
- `go/` houses the Go CLI implementation (single binary). Entry point: `go/main.go`.
- `python/` contains the reference Python CLI (`python/atf.py`).
- `docs/` is long-form documentation and design notes.
- `examples/` holds sample `.atf` files used for quick manual checks.
- `install/` and `installers/` include installer scripts and packaging assets.
- Root docs like `README.md`, `SPECIFICATION.md`, and `CONTRIBUTING.md` define the format and contributor workflow.

## Build, Test, and Development Commands
- Ensure Go is in your PATH
- Build binary: `go build -o atf ./go` (run from repository root)
- Run commands: `./atf rebuild examples/simple.atf`
- Validate: `./atf validate examples/simple.atf`
- Python alternative: `python python/atf.py rebuild examples/simple.atf`
- **Note:** All commands above are intended to be run from the repository root directory
- **Windows users:** Use `atf.exe` instead of `atf` in commands, and the build command produces `atf.exe`: `go build -o atf.exe ./go`

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indentation, type hints where helpful, and docstrings for functions.
- Go: `gofmt` formatting, idiomatic names, and comments on exported functions.
- Branch naming follows `feature/your-feature-name`.

## Testing Guidelines
- No dedicated test suite is present yet. Validate changes by running the five commands (rebuild, rebuild-all, watch, unwatch, validate) on files in `examples/`.
- Always do manual testing for task requirements in both implementations: build/run/validate with the Go CLI and run the equivalent commands with the Python CLI.
- Go tests are noted as TODO; `go test` should remain clean if added.

## Documentation Guidelines
- Do not repeat information across docs. If something is explained in one place, reference it rather than duplicating.
- Keep docs DRY (Don't Repeat Yourself) - single source of truth for each concept.

## Commit & Pull Request Guidelines
- Auto commits and PR's NOT ALLOWED.

## Security & Configuration Notes
- Python watch state is stored in `~/.atf/watch.json`; avoid committing user-specific state.
- If you modify installers, verify behavior on at least one target platform.

## Problem Statement
ATF exists to make large documents navigable for AI agents without loading entire files or wasting tokens. Instead of requiring RAG-style pipelines, the format works with simple grep-like tools as models get smarter about retrieval. ATF files can define the full scope of work (requirements, flows, test cases, and expected outcomes) in single file for small hobby projects and divided in multiple atf files for larger projects so agents can look up the exact section they need via the INDEX and act on it quickly.
