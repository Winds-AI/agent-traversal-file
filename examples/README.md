# IATF Example Corpus (E2E Testing)

This folder contains an end-to-end test corpus for the current IATF CLI and validator.

## Structure

- `simple.iatf`
  - Canonical smoke-test fixture used by Go tests and manual checks.
- `incident-playbook.iatf`
  - Quickstart-focused file for `index`, `find`, `read`, and `graph` demos.
- `cross-references.iatf`
  - Root-level graph/reference fixture for docs compatibility.
- `valid/`
  - Additional valid fixtures with different structure patterns.
- `warnings/`
  - Structurally valid fixtures expected to return warnings.
- `invalid/`
  - Fixtures expected to fail validation.

## Valid Fixtures

- `examples/simple.iatf`
  - Basic 3-section document with summaries and one reference.
- `examples/incident-playbook.iatf`
  - Incident workflow with cross references and command snippets.
- `examples/cross-references.iatf`
  - Multiple sections with references; includes fenced code containing a fake reference.
- `examples/valid/cross-references.iatf`
  - Same scenario as root fixture for directory-based test runs.
- `examples/valid/nested-runbook.iatf`
  - Two-level nested sections (maximum supported depth).
- `examples/valid/no-index-bootstrap.iatf`
  - CONTENT-first file intended for first-time `iatf rebuild` bootstrap testing.

## Warning Fixture

- `examples/warnings/stale-index.iatf`
  - Expected: `iatf validate` succeeds with stale `Content-Hash` warning.
- `examples/warnings/no-index-yet.iatf`
  - Expected: `iatf validate` succeeds with "No INDEX section" warning until first rebuild.

## Invalid Fixtures (Expected `validate` failure)

- `examples/invalid/duplicate-id.iatf`
  - Duplicate section IDs.
- `examples/invalid/broken-reference.iatf`
  - Reference to missing section.
- `examples/invalid/self-reference.iatf`
  - Self-reference in section body.
- `examples/invalid/unclosed-section.iatf`
  - Missing closing section tag.
- `examples/invalid/content-outside-section.iatf`
  - Stray content outside any section block.
- `examples/invalid/index-after-content.iatf`
  - Delimiter order violation (`INDEX` appears after `CONTENT`).
- `examples/invalid/nesting-depth-3.iatf`
  - Third-level nested section (validator limit is depth 2).

## Manual E2E Command Set

```bash
# Build local CLI once from repo root
GOCACHE=/tmp/go-build-cache GOMODCACHE=/tmp/go-mod-cache go build -o iatf ./go

# Rebuild valid fixtures only
./iatf rebuild examples/simple.iatf
./iatf rebuild examples/incident-playbook.iatf
./iatf rebuild examples/cross-references.iatf
./iatf rebuild-all examples/valid

# Optional warning fixture bootstrap
./iatf rebuild examples/warnings/no-index-yet.iatf

# Validate expected-pass fixtures
./iatf validate examples/simple.iatf
./iatf validate examples/incident-playbook.iatf
./iatf validate examples/cross-references.iatf
./iatf validate examples/valid/cross-references.iatf
./iatf validate examples/valid/nested-runbook.iatf
./iatf validate examples/valid/no-index-bootstrap.iatf
./iatf validate examples/warnings/stale-index.iatf

# Validate expected-fail fixtures
for f in examples/invalid/*.iatf; do
  ./iatf validate "$f"
done

# Navigation checks
./iatf index examples/incident-playbook.iatf
./iatf find examples/incident-playbook.iatf rollback
./iatf read examples/incident-playbook.iatf rollback
./iatf graph examples/incident-playbook.iatf
./iatf graph examples/incident-playbook.iatf --show-incoming
```
