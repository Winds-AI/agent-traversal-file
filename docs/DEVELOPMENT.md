# Development Guide

## Contribution Flow

1. Open an issue (bug/feature) with repro and expected behavior.
2. Create a branch: `feature/<name>` or `fix/<name>`.
3. Implement changes and keep scope narrow.
4. Run required checks before PR:
   - `cd go && go test ./...`
   - `./iatf validate <changed-fixture.iatf>` for fixture/doc changes
5. Open PR with:
   - concise summary
   - behavioral impact
   - test evidence

## Coding Standards

### Go

- Format with `gofmt`.
- Prefer small, explicit functions over deep abstraction.
- Keep parser/validator behavior deterministic (stable ordering, predictable output).
- When format behavior changes, update docs and examples in the same PR.

### CLI/Format Changes

- `CONTENT` remains source of truth.
- `INDEX` is generated; do not hand-edit generated metadata in normal workflows.
- Keep command output agent-friendly and machine-parseable.

## Git Rules

- Do not auto-commit or auto-create PRs without explicit approval.
- Use conventional commit prefixes when committing (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).
- Avoid unrelated file changes in the same PR.

## Security and Local State

- Never commit user-local state files under `~/.iatf/`.
- Installer changes must preserve checksum/integrity verification behavior.
- Treat watch/daemon path configs as environment-specific, not repository config.

## LSP Status

- LSP exists under `lsp/` and is actively evolving.
- Keep CLI and LSP parser behavior aligned for syntax and diagnostics.
