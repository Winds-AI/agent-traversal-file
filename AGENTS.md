# IATF Agent Guidelines

**IATF** makes large documents navigable for AI agents without loading entire files or wasting tokens. IATF files define project scope (requirements, flows, test cases, expected outcomes) in a single file for small projects or multiple files for larger projects, so agents can look up exact sections via the INDEX.

## Quick Commands
```bash
# Validate file
./iatf validate examples/simple.iatf

# Rebuild INDEX
./iatf rebuild examples/simple.iatf
```

**Windows:** Use `iatf.exe` instead of `iatf`.

## Project Structure

- `go/` - Go CLI implementation (entry: `go/main.go`)
- `examples/` - Sample `.iatf` files for testing
- `installers/` - Installer scripts
- `docs/` - Additional documentation (see links below)

## Documentation Maintenance

When user-approved changes affect conventions, workflows, or project structure:

1. Update relevant AGENTS.md sections immediately
2. Ensure consistency across all linked documentation
3. Verify cross-references still work
4. Never duplicate information - reference instead

## Detailed Guides

- [Coding Standards](docs/coding-standards.md) - Go conventions and branch naming
- [Testing](docs/testing.md) - Manual testing requirements
- [CI/CD & Release](docs/ci-cd-release.md) - GoReleaser workflow and release process
- [Security](docs/security.md) - Configuration and installer security
- [Git Workflow](docs/git-workflow.md) - Commit and PR guidelines
- [All Comands](docs/COMMANDS.md) - How to use each available command
