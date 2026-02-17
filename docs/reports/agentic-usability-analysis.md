# Agentic Usability Analysis: IATF

Date: 2026-02-17

## Scope

This report evaluates whether IATF's index-first traversal model is practically useful for agentic workflows.

Requested constraints followed:
- Did not run scripts from `benchmark/`.
- Replaced and rebuilt the `examples/` corpus for end-to-end manual testing.
- Used subagents with different operating constraints.
- Used OpenAI tokenizer (`tiktoken`) for exact token accounting.

## 1. Pre-Evaluation Alignment Audit (Docs vs Implementation)

### Verified mismatches

1. `watch --list` behavior text mismatch.
- Doc previously claimed no output when empty.
- CLI actually prints `No files are being watched`.
- Evidence: `docs/COMMANDS.md:131`, `go/main.go:1217`.
- Status: fixed in docs.

2. Testing docs claimed no automated suite.
- Repo has Go tests in `go/main_test.go`.
- Evidence: `docs/testing.md:3`, `go/main_test.go:11`.
- Status: fixed in docs.

3. README linked a non-existent analysis path.
- Evidence: `README.md:38` previously pointed to `docs/agentic-usability-analysis.md`.
- Status: fixed to `docs/reports/agentic-usability-analysis.md`.

4. LSP parser behavior had diverged from CLI/spec (fixed after this report’s initial draft).
- Section tags are now anchored in LSP to match CLI (`lsp/analyzer/analyzer.go`, `go/main.go`).
- Code-fence toggling now matches CLI/spec: only lines exactly equal to ````` toggle fence state.
- Duplicate-ID diagnostic line numbers now use numeric formatting.
- Added parity-focused LSP tests: `lsp/analyzer/analyzer_test.go`.

## 2. Example Corpus Rebuild

The old `examples/` corpus was removed and replaced with a broader E2E suite.

### Added/updated valid fixtures

- `examples/simple.iatf`
- `examples/incident-playbook.iatf`
- `examples/cross-references.iatf`
- `examples/product-ops-manual.iatf`
- `examples/scalability-handbook.iatf` (40 sections)
- `examples/valid/cross-references.iatf`
- `examples/valid/nested-runbook.iatf`
- `examples/valid/multiline-summary.iatf`
- `examples/valid/header-custom-field.iatf`

### Warning fixtures

- `examples/warnings/no-index-yet.iatf`
- `examples/warnings/stale-index.iatf`
- `examples/warnings/missing-content-hash.iatf`

### Invalid fixtures

- `examples/invalid/broken-reference.iatf`
- `examples/invalid/content-outside-section.iatf`
- `examples/invalid/duplicate-id.iatf`
- `examples/invalid/index-after-content.iatf`
- `examples/invalid/index-content-mismatch.iatf`
- `examples/invalid/nesting-depth-3.iatf`
- `examples/invalid/self-reference.iatf`
- `examples/invalid/unclosed-section.iatf`
- `examples/invalid/unsupported-annotation.iatf`

### Validation sweep result

All fixtures matched expected outcomes:
- valid: pass, no warnings
- warnings: pass, warning-only
- invalid: fail

## 3. Subagent Behavior Trials

Three agent profiles were used per scenario:
- strict IATF-only flow
- shell-only flow (`rg`/`sed`/`awk`, no `iatf`)
- unrestricted explorer profile

### Scenario A: Product Ops QA (5 multi-hop questions)

Result:
- All three answered correctly.

Behavioral notes:
- IATF-only agent used many small calls (`index`/`find`/`read`/`graph`), but stayed explicit about section IDs.
- Shell-only agent answered correctly with fewer commands, but depended on manual line-window extraction.
- Explorer used index+targeted reads and was concise.

### Scenario B: Cross-reference + fenced-code edge case

Result:
- All three answered correctly.

Behavioral notes:
- IATF and explorer flows handled code-fence semantics directly.
- Shell-only flow required custom `awk` logic for fence-aware extraction and had a quoting misstep during one command.
- This is where IATF gives stronger reliability: graph semantics are encoded, not reimplemented ad hoc each run.

## 4. Exact Token Analysis (OpenAI Tokenizer)

Tokenizer:
- library: `tiktoken`
- model encoding resolved to: `o200k_base` for both `gpt-4o-mini` and `gpt-5-mini` on this date.

Counting method:
- Tokenized command transcripts (`$ <command>` + command output) for each strategy.
- Compared:
  - full-file load
  - IATF index-first flow
  - shell search flow (`rg`/`sed`/`awk`)

### Measured totals (tokens)

| Scenario | Full File | IATF Flow | Shell Flow |
|---|---:|---:|---:|
| Product Ops (medium file, broad retrieval) | 1032 | 1062 | 1331 |
| Cross Refs (edge-case reasoning) | 597 | 475 | 748 |
| Scalability Sparse (40-section file) | 6021 | 2138 | 2695 |

### Savings / deltas

- Product Ops:
  - IATF vs shell: **20.21% fewer tokens**
  - IATF vs full-file: **2.91% more tokens** (small file + many targeted reads)

- Cross Refs:
  - IATF vs shell: **36.50% fewer tokens**
  - IATF vs full-file: **20.44% fewer tokens**

- Scalability Sparse:
  - IATF vs shell: **20.67% fewer tokens**
  - IATF vs full-file: **64.49% fewer tokens**

## 5. Index Size Observations

Two different "index size" views matter:

1. Persisted INDEX block inside file currently remains large due rich per-section metadata (dates/hashes/line ranges).
- `examples/simple.iatf`: 53.55% of total tokens
- `examples/incident-playbook.iatf`: 51.73%
- `examples/product-ops-manual.iatf`: 50.10%
- `examples/scalability-handbook.iatf`: 43.57%

2. `iatf index` command output is much smaller than full file because it omits comments/hash lines and section bodies.
- ~20-23% of total file tokens across tested fixtures.

Implication: the "INDEX is tiny" claim is true at command-output level, not for the raw stored index block in the file.

## 6. Is the Philosophy Useful for Agentic Models?

Short answer: **Yes, conditionally.**

Where it clearly helps:
- Large docs with sparse retrieval needs.
- Graph/reference-heavy tasks where fence-aware semantics matter.
- Workflows needing deterministic section IDs and validation barriers.

Where gains are weaker:
- Small/medium files where reading most sections anyway is cheaper than many command round-trips.
- Agents not instructed to follow index-first flow (they may default to `rg`/`sed` heuristics).

So the progressive-disclosure/Table-of-Contents philosophy is aligned with agent behavior, but performance depends on retrieval sparsity and instruction quality.

## 7. Recommendations to Improve Real-World Efficiency

Completed since initial draft:
- compact default index output with optional `--with-dates`
- `iatf read-many <ids...>`
- LSP parser alignment for anchored tags and exact fence handling

Remaining recommendations:
1. Add integration tests for doc-behavior claims (especially command output semantics).
2. Keep prompting strict for agents: index/find/read/graph-first flow materially improves consistency.

## 8. Repro Commands (Core)

```bash
# Validate the full corpus
for f in examples/*.iatf examples/valid/*.iatf examples/warnings/*.iatf; do
  ./iatf validate "$f"
done
for f in examples/invalid/*.iatf; do
  ./iatf validate "$f"
done

# Sample navigation
./iatf index examples/product-ops-manual.iatf
./iatf find examples/product-ops-manual.iatf "SLA breach risk"
./iatf read examples/product-ops-manual.iatf sla-policy
./iatf graph examples/cross-references.iatf --show-incoming
```
