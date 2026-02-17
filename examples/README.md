# IATF Example Corpus (E2E Testing)

This corpus is designed for end-to-end validation of the current CLI and parser behavior.

## Layout

- `examples/simple.iatf`
  - Small smoke test for `rebuild`, `validate`, `index`, `find`, and `read`.
- `examples/incident-playbook.iatf`
  - Operational workflow fixture with references for realistic navigation.
- `examples/cross-references.iatf`
  - Graph/reference fixture with fenced-code edge cases.
- `examples/product-ops-manual.iatf`
  - Larger multi-section fixture for agentic retrieval and token analysis.
- `examples/scalability-handbook.iatf`
  - Large 40-section fixture for sparse-retrieval and token-scaling evaluation.
- `examples/valid/`
  - Valid fixtures covering nesting, multiline summaries, and header metadata tolerance.
- `examples/warnings/`
  - Warning-only fixtures (validation exit code 0).
- `examples/invalid/`
  - Error fixtures (validation exit code 1).

## Expected Validation Outcomes

### Valid (`validate` succeeds with no warnings)

- `examples/simple.iatf`
- `examples/incident-playbook.iatf`
- `examples/cross-references.iatf`
- `examples/product-ops-manual.iatf`
- `examples/scalability-handbook.iatf`
- `examples/valid/cross-references.iatf`
- `examples/valid/nested-runbook.iatf`
- `examples/valid/multiline-summary.iatf`
- `examples/valid/header-custom-field.iatf`

### Warning-Only (`validate` succeeds with warnings)

- `examples/warnings/no-index-yet.iatf`
  - Missing INDEX (bootstrap scenario).
- `examples/warnings/stale-index.iatf`
  - INDEX hash intentionally stale.
- `examples/warnings/missing-content-hash.iatf`
  - INDEX exists but missing Content-Hash comment.

### Invalid (`validate` fails)

- `examples/invalid/broken-reference.iatf`
- `examples/invalid/content-outside-section.iatf`
- `examples/invalid/duplicate-id.iatf`
- `examples/invalid/index-after-content.iatf`
- `examples/invalid/index-content-mismatch.iatf`
- `examples/invalid/nesting-depth-3.iatf`
- `examples/invalid/self-reference.iatf`
- `examples/invalid/unclosed-section.iatf`
- `examples/invalid/unsupported-annotation.iatf`

## Suggested Manual E2E Sweep

```bash
# Build CLI from source
GOCACHE=/tmp/go-build-cache GOMODCACHE=/tmp/go-mod-cache go build -o iatf ./go

# Rebuild core/valid fixtures
./iatf rebuild examples/simple.iatf
./iatf rebuild examples/incident-playbook.iatf
./iatf rebuild examples/cross-references.iatf
./iatf rebuild examples/product-ops-manual.iatf
./iatf rebuild-all examples/valid

# Validate valid and warning fixtures
for f in examples/*.iatf examples/valid/*.iatf examples/warnings/*.iatf; do
  ./iatf validate "$f"
done

# Validate invalid fixtures (expected non-zero)
for f in examples/invalid/*.iatf; do
  ./iatf validate "$f"
done

# Navigation checks
./iatf index examples/incident-playbook.iatf
./iatf find examples/product-ops-manual.iatf "incident escalation sla"
./iatf read examples/product-ops-manual.iatf escalation
./iatf graph examples/cross-references.iatf
./iatf graph examples/cross-references.iatf --show-incoming
```
