# IATF Agent Guidelines

IATF is optimized for index-first retrieval in large structured docs.

## Quick Commands

```bash
./iatf rebuild examples/simple.iatf
./iatf validate examples/simple.iatf
```

Windows: use `iatf.exe`.

## Project Structure

- `go/`: Go CLI (`go/main.go`)
- `lsp/`: Go LSP server (`lsp/main.go`)
- `examples/`: validation/test fixtures
- `installers/`: install scripts
- `docs/`: documentation

## Documentation Maintenance

When behavior changes:

1. Update `docs/SPECIFICATION.md` for format/validation changes.
2. Update `docs/COMMANDS.md` / `docs/QUICKSTART.md` for command UX changes.
3. Keep `examples/` aligned with current parser behavior.
4. Keep links in `docs/README.md` and this file valid.

## Doc Entry Points

- `docs/README.md`: doc map
- `docs/DEVELOPMENT.md`: contribution/coding/git/security rules
- `docs/testing.md`: test expectations
- `docs/ci-cd-release.md`: release flow
- `docs/COMMANDS.md`: CLI behavior
