# IATF Efficiency Benchmark Report

Date: February 18, 2026  
Repository: `agent-traversal-file`

## 1. Objective

Evaluate whether IATF provides token-efficient and accuracy-preserving retrieval for large, realistic product documentation compared to standard shell-based retrieval.

## 2. Scope and Constraints

- Benchmark executed with spawned sub-agents in this Codex harness session.
- Harness limitation: sub-agents could not be explicitly configured to different model names/reasoning levels.
- Token counting used `tiktoken` with GPT-5 mapping (`o200k_base`).
- For fairness, answering agents used `questions_only.yaml` (no gold answers).

## 3. Dataset Built for This Run

Generated during this session:

- `subagent_live_benchmark/dataset_frd/document.txt`
  - 1990 lines
- `subagent_live_benchmark/dataset_frd/document.iatf`
  - 2471 lines
  - 67 indexed sections
  - validated with `iatf v1.1.12`
- `subagent_live_benchmark/dataset_frd/questions.yaml`
  - 18 questions (6 needle, 6 multihop, 6 aggregation)
- `subagent_live_benchmark/dataset_frd/questions_only.yaml`
  - stripped benchmark input (no expected answers)

Domain used: enterprise procurement + AP automation SaaS.

## 4. Approaches Tested

Three sub-agent arms answered the same 18 questions:

1. `iatf_primed`
   - Retrieval against `document.iatf`
   - Allowed commands: `iatf index/find/read/read-many/graph`
2. `shell_guided`
   - Retrieval against `document.txt`
   - Standard shell commands (`rg/sed/...`) with a small hint
3. `shell_unguided`
   - Retrieval against `document.txt`
   - Standard shell commands without retrieval hint

All command executions were logged through:
- `subagent_live_benchmark/runlog.sh`

Logs and outputs:
- `subagent_live_benchmark/runs/iatf_primed/tool.log`
- `subagent_live_benchmark/runs/shell_guided/tool.log`
- `subagent_live_benchmark/runs/shell_unguided/tool.log`
- `subagent_live_benchmark/runs/*/answers.yaml`

## 5. Measurement Method

Metrics were computed by:
- `subagent_live_benchmark/scripts/analyze_runs.py`

Inputs:
- command strings
- raw stdout/stderr
- produced answers
- question `must_include` keys

Primary metrics:
- tool I/O tokens (`command + output`)
- exact-match count (`all must_include` present)
- mean must-include recall
- efficiency: `tool I/O tokens / exact-match question`

Tokenizer:
- model: `gpt-5`
- encoding: `o200k_base`

## 6. Results

From `subagent_live_benchmark/results/metrics.json` and `subagent_live_benchmark/results/report.md`:

| Approach | Tool I/O Tokens | Exact Match (all must_include) | Mean must_include Recall |
|---|---:|---:|---:|
| `iatf_primed` | 23,574 | 5/18 | 0.571 |
| `shell_guided` | 23,104 | 3/18 | 0.596 |
| `shell_unguided` | 20,955 | 1/18 | 0.534 |

Efficiency (Tool I/O tokens per exact-match question):

| Approach | Tokens / Exact |
|---|---:|
| `iatf_primed` | 4,714.80 |
| `shell_guided` | 7,701.33 |
| `shell_unguided` | 20,955.00 |

Derived comparisons:
- `iatf_primed` vs `shell_guided`: ~38.8% better quality-normalized efficiency.
- `iatf_primed` vs `shell_unguided`: ~77.5% better quality-normalized efficiency.

## 7. Index Overhead / Sweet-Spot Signal

Observed index-token share in `.iatf` files:

- `examples/simple.iatf`: ~50.5%
- `examples/incident-playbook.iatf`: ~48.2%
- `examples/product-ops-manual.iatf`: ~46.6%
- `examples/scalability-handbook.iatf`: ~39.9%
- new large FRD `document.iatf`: ~12.7%

Interpretation:
- For small docs, index overhead is high.
- For large, structured docs, index overhead drops substantially and becomes practical.
- This supports IATF’s intended use for large docs and repeated targeted retrieval.

## 8. Validation of Existing Example Corpus

Ran validation sweep on `iatf v1.1.12`:
- valid fixtures: valid
- warning fixtures: warning-only
- invalid fixtures: invalid

No immediate changes were required to `examples/` for this benchmark run.

## 9. Limitations

- Sub-agents in this harness were not model-mixed by explicit model/reasoning configuration.
- Accuracy metric is lexical (`must_include`) and not full semantic grading.
- Agent strategies included some broad reads; tighter per-question retrieval budgets would improve discriminative power.
- A small one-time prompt/setup overhead exists for command-learning in IATF arm.

## 10. Conclusions

- IATF showed stronger efficiency when normalized by answer quality in this run.
- Raw token usage alone is not enough; quality-normalized efficiency is the key metric.
- The practical sweet spot appears to be medium/large documents with many sections and repeated pinpoint retrieval needs.

## 11. Recommended Next Benchmark Iteration

1. Run multiple seeds/repeats for variance and confidence intervals.
2. Add semantic LLM judge scoring in addition to `must_include`.
3. Enforce hard retrieval budgets per question (max commands / max bytes returned).
4. Run explicit model matrix via `opencode` for cross-model behavior.
5. Evaluate multi-file IATF directory + top-level index scenario (horizontal scaling).

