# Contributing

For day-to-day engineering rules, start with `docs/DEVELOPMENT.md`.

## Open Issues First

Before opening a PR, open or confirm an issue for the change when possible.

Include:
- problem statement
- expected behavior
- minimal repro
- environment details (`iatf --version`, OS)

## Pull Request Checklist

- Scope is focused and justified.
- Behavior changes are reflected in:
  - `docs/SPECIFICATION.md`
  - `docs/COMMANDS.md` or `docs/QUICKSTART.md` (as needed)
  - `examples/` fixtures (if format/validation behavior changed)
- Validation evidence included:
  - `go test ./...`
  - relevant `iatf validate` / command outputs

## Areas For Help

- Additional LSP diagnostics/completions parity with CLI.
- Cross-platform watch/daemon reliability testing.
- More integration tests for command output contracts.
- Documentation quality and concise examples.
