# IATF Agentic Usability Analysis

Date: 2026-02-17
Scope: Local CLI + example corpus + manual/subagent trials (no benchmark scripts executed)

## Executive Conclusion

The philosophy is useful for agentic models when tasks are section-discoverable and retrieval is constrained to targeted sections. In this repo's current implementation, index-first traversal consistently reduced retrieval payload in the tested workflows while preserving answer quality.

It is not automatically useful by default: agents still need explicit behavior constraints (`index/find/read/graph` first) or they drift into full-file reads.

## What Was Tested

### 1) End-to-End Example Corpus Replacement

`examples/` was rebuilt as a test corpus with expected outcomes:

- Valid fixtures:
  - `examples/simple.iatf`
  - `examples/incident-playbook.iatf`
  - `examples/cross-references.iatf`
  - `examples/valid/cross-references.iatf`
  - `examples/valid/nested-runbook.iatf`
  - `examples/valid/no-index-bootstrap.iatf`
- Warning fixtures:
  - `examples/warnings/no-index-yet.iatf`
  - `examples/warnings/stale-index.iatf`
- Invalid fixtures:
  - `examples/invalid/duplicate-id.iatf`
  - `examples/invalid/broken-reference.iatf`
  - `examples/invalid/self-reference.iatf`
  - `examples/invalid/unclosed-section.iatf`
  - `examples/invalid/content-outside-section.iatf`
  - `examples/invalid/index-after-content.iatf`
  - `examples/invalid/nesting-depth-3.iatf`

Validation status after migration:

- Valid fixtures: pass (`exit=0`)
- Warning fixtures: valid with warnings (`exit=0`)
- Invalid fixtures: fail (`exit=1`)

### 2) Command Coverage

Tested manually against the new corpus:

- `rebuild`
- `rebuild-all`
- `validate`
- `index` + `--with-dates`
- `find`
- `read` by ID and by title
- `graph` and `graph --show-incoming`

### 3) Subagent Behavior Trials

Three subagents were run on the same question set:

- Baseline full-read strategy (`cat`/`rg` only)
- Progressive IATF strategy (`index/find/read/graph`)
- Naive direct-read strategy (`index/read`, no `find`/`graph`)

All three answered correctly on the selected questions. Differences were in retrieval cost and operator friction.

## Quantitative Results

### Index size vs full file size (bytes)

- `examples/incident-playbook.iatf`: full `1752`, index output `274` (15.6%)
- `examples/cross-references.iatf`: full `1953`, index output `429` (22.0%)
- `examples/valid/nested-runbook.iatf`: full `2049`, index output `532` (26.0%)
- `examples/simple.iatf`: full `1390`, index output `216` (15.5%)

Note: On small files, index share is higher than the "~5%" target often cited in docs. This is expected overhead behavior for short documents.

### Workflow retrieval payload comparison (bytes returned by commands)

- Incident follow-up question:
  - Baseline full read: `1752`
  - IATF traversal (`index + read rollback + graph incoming`): `703`
  - Reduction: ~59.9%
- Fake-target edge check question:
  - Baseline full read: `1953`
  - IATF traversal (`graph + read incident-flow`): `453`
  - Reduction: ~76.8%
- Auth escalation question:
  - Baseline full read: `1953`
  - IATF traversal (`read overview + read authentication`): `434`
  - Reduction: ~77.8%

## Implementation Findings

### Fixed in this work

1. First rebuild line-range instability
- Symptom: a content-only file could fail `validate` after first `rebuild` with INDEX line-range mismatches, then pass after a second rebuild.
- Root cause: line-range adjustment depended on a one-shot delta estimate.
- Fix: rebuild now recalculates section ranges from the first assembled output and emits a corrected final index in one rebuild.
- File: `go/main.go`

2. Section title overwrite by later headings
- Symptom: section title could become the last heading in a section instead of the first heading.
- Fix: title is now set from the first markdown heading only (or falls back to section ID).
- File: `go/main.go`

### Spec/implementation mismatches still present

1. Reserved header metadata enforcement
- Spec text says only reserved header fields should be preserved/supported.
- Current validator accepts additional header metadata fields (example: `@owner:`) without warning/error.

2. AUTO-GENERATED marker validation
- The marker line in INDEX is described as required in spec docs.
- Current validator does not explicitly enforce marker text content.

## Practical Guidance for Agentic Use

1. Enforce retrieval policy in agent prompts
- Require `iatf index/find/graph` before broad reads.
- Disallow raw full-file reads unless confidence remains low after targeted traversal.

2. Keep summaries high-signal
- `@summary` quality strongly drives find/ranking usefulness.

3. Use graph for multi-hop tasks
- Incoming/outgoing relations reduce manual reconstruction errors.

4. Run validate in loops
- Treat `validate` as a guardrail, especially in autonomous edit workflows.

5. Use the corpus as regression suite
- The new `examples/` structure is designed to quickly regression-test parser, reference, and delimiter behavior.
