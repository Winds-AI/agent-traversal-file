# IATF Improvement Plan

You’re asking the right question. Right now your benchmark is mixing two things:

1. “Is IATF inherently better?”
2. “Did the model use IATF correctly this run?”

Those must be separated.

## What your recent runs show

1. IATF can be efficient (`~10k tokens`) when the model follows `index -> targeted read`.
2. IATF can also be very expensive (`~60k+ tokens`) with the same question when step context is replayed and cache reuse is poor.
3. So your current variance is mostly **agent behavior + harness design**, not necessarily IATF format quality.

## Highest-impact improvements (do these first)

1. Harden the IATF benchmark prompt in `benchmark/prompts/iatf.md`.
- Force a strict policy: `iatf index` once, max 2-3 targeted `iatf read`, no full-file `read`.
- Require answer to include source section IDs used.
- Add explicit “stop after enough evidence” rule.

2. Isolate skills deterministically in benchmark runs (`benchmark/benchlib/opencode_runner.py`).
- For iatf approach, use temp HOME and copy only `iatf` skill into it.
- Do not depend on whatever global skills happen to exist.
- This removes huge run-to-run drift.

3. Add run-level guardrails (treat violation as invalid run).
- If IATF run calls generic full-file `read` on `.iatf`, mark as policy violation.
- If wrong skill is loaded, mark invalid.
- If tool calls exceed budget for question type, flag it.

4. Report better token metrics in `benchmark/benchlib/summary.py`.
- Keep current totals, but add:
- `net_input_tokens = prompt_tokens - cache_read_tokens`
- step count
- median tokens/latency (not just avg)
- p90/p95 latency
Averages hide your instability.

5. Run each question multiple times (n=3 or n=5).
- Use median for comparison, not single-run values.
- You need stability claims, not one lucky pass.

## Benchmark design upgrades (to prove true IATF benefit)

1. Add retrieval-quality metrics (not only final answer accuracy).
- You already have `requires_sections` in dataset.
- Compute retrieval recall: did agent fetch required sections?
- Compute retrieval precision: how much fetched content was actually relevant?
- Compute over-read ratio: bytes/tokens loaded vs minimum needed.

2. Compare under controlled modes.
- `Agent-Freeform`: current style.
- `Agent-Policy-Constrained`: strict IATF workflow.
- `Deterministic-Retriever + LLM Answer`: scripted retrieval, same answer model.
This tells you whether gains come from format or from prompting luck.

3. Benchmark across document scales.
- On small docs, IATF overhead may dominate.
- On medium/large docs, IATF should win if retrieval is section-scoped.
- Use at least 3 sizes and plot scaling curves.

4. Separate startup overhead from query latency.
- Especially for RAG (server/model warmup).
- Measure steady-state latency and cold-start latency separately.

## IATF skill improvements

1. Keep the new pipeline patterns you added, and add strict anti-patterns.
- “Never load entire `.iatf` file with generic read.”
- “Never run validation unless asked.”
- “Prefer section IDs from index, then read only those.”

2. Add question-type playbooks inside the skill.
- `needle`: 1 index + 1 read.
- `contradiction`: `questions` + one topic section.
- `multihop`: start from seed sections, then one-hop via references.

3. Add token budget guidance.
- “If >3 reads and still uncertain, summarize evidence and stop.”

## IATF core logic improvements (big leverage)

1. Add machine-readable CLI outputs in `go/main.go`.
- `iatf index --json`
- `iatf read --json`
- This reduces verbose formatting tokens and parsing errors.

2. Add a first-class search command.
- `iatf find <file> <query>` returning ranked section IDs from index summaries/titles.
- Agent should not need custom grep loops every run.

3. Add bounded read options.
- `iatf read <file> <id> --max-lines N` or `--max-chars N`
- Prevent accidental huge context injection.

4. Add multi-read command.
- `iatf read-many <file> id1 id2 ...` with compact separators.
- Fewer tool turns, less repeated context replay.

## What “good” should look like (acceptance targets)

1. IATF policy-constrained runs: 0 full-file reads.
2. Needle/contradiction: median tool calls <=3.
3. IATF median net input tokens lower than baseline by a clear margin.
4. Accuracy non-inferior to baseline (or better).
5. Variance reduced: coefficient of variation on tokens/latency much lower than now.
