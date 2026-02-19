#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import tiktoken
import yaml


@dataclass
class ToolEntry:
    cmd: str
    exit_code: int
    stdout: str
    stderr: str


@dataclass
class ApproachMetrics:
    name: str
    tool_calls: int
    retrieval_tool_calls: int
    cmd_tokens: int
    out_tokens: int
    io_tokens: int
    retrieval_cmd_tokens: int
    retrieval_out_tokens: int
    retrieval_io_tokens: int
    answer_tokens: int
    answered: int
    exact_match_all: int
    mean_must_include_recall: float
    violations: List[str]


def parse_tool_log(path: Path) -> List[ToolEntry]:
    text = path.read_text(encoding="utf-8", errors="replace")
    entries: List[ToolEntry] = []
    chunks = text.split("-----\n")
    for chunk in chunks:
        if not chunk.startswith("CMD: "):
            continue
        try:
            cmd, rest = chunk[5:].split("\nEXIT: ", 1)
            exit_text, rest = rest.split("\nSTDOUT<<EOF\n", 1)
            stdout, rest = rest.split("\nEOF\nSTDERR<<EOF\n", 1)
            if rest.endswith("\nEOF\n"):
                stderr = rest[:-5]
            elif rest.endswith("EOF\n"):
                stderr = rest[:-4]
            elif rest.endswith("\nEOF"):
                stderr = rest[:-4]
            else:
                raise ValueError("stderr terminator not found")
            entries.append(
                ToolEntry(
                    cmd=cmd,
                    exit_code=int(exit_text.strip()),
                    stdout=stdout,
                    stderr=stderr,
                )
            )
        except Exception:
            # Keep analysis resilient even if one log entry is malformed.
            continue
    return entries


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def score_answers(questions: List[dict], answers: Dict[str, str]) -> Tuple[int, float, int]:
    exact = 0
    recall_sum = 0.0
    answered = 0
    for q in questions:
        qid = q["id"]
        ans = answers.get(qid, "")
        if not ans.strip():
            continue
        answered += 1
        ans_norm = normalize(ans)
        required = [normalize(k) for k in q.get("must_include", [])]
        if not required:
            continue
        hit = sum(1 for k in required if k in ans_norm)
        if hit == len(required):
            exact += 1
        recall_sum += hit / len(required)
    mean_recall = (recall_sum / len(questions)) if questions else 0.0
    return exact, mean_recall, answered


def load_answers(path: Path) -> Dict[str, str]:
    obj = yaml.safe_load(path.read_text(encoding="utf-8"))
    out: Dict[str, str] = {}
    for row in obj.get("answers", []):
        out[str(row.get("id"))] = str(row.get("answer", ""))
    return out


def detect_violations(name: str, entries: List[ToolEntry]) -> List[str]:
    v: List[str] = []
    for e in entries:
        cmd = e.cmd
        low = cmd.lower()
        if "questions.yaml" in low:
            v.append("opened_gold_answer_file")
        if name == "iatf_primed":
            if "document.iatf" in low and any(tok in low for tok in [" cat ", " rg ", " grep ", " sed ", " awk "]):
                v.append("non_iatf_doc_retrieval")
        if name in {"shell_guided", "shell_unguided"} and re.search(r"(^|[;&|()\s])iatf(\s|$)", low):
            v.append("used_iatf_in_shell_arm")
    # Deduplicate while preserving order
    seen = set()
    out = []
    for item in v:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def analyze(root: Path, model: str) -> dict:
    questions_obj = yaml.safe_load((root / "dataset_frd/questions.yaml").read_text(encoding="utf-8"))
    questions = questions_obj["questions"]

    enc = tiktoken.encoding_for_model(model)

    run_dirs = [
        ("iatf_primed", root / "runs/iatf_primed"),
        ("shell_guided", root / "runs/shell_guided"),
        ("shell_unguided", root / "runs/shell_unguided"),
    ]

    metrics: List[ApproachMetrics] = []
    for name, run_dir in run_dirs:
        entries = parse_tool_log(run_dir / "tool.log")
        answers = load_answers(run_dir / "answers.yaml")

        cmd_tokens = 0
        out_tokens = 0
        retrieval_cmd_tokens = 0
        retrieval_out_tokens = 0
        retrieval_tool_calls = 0
        for e in entries:
            cmd_tok = len(enc.encode(e.cmd))
            out_tok = len(enc.encode(e.stdout + ("\n" if e.stdout and e.stderr else "") + e.stderr))
            cmd_tokens += cmd_tok
            out_tokens += out_tok
            # Filter out obvious post-processing/file-write verification commands.
            is_overhead = (
                "/runs/" in e.cmd
                and ("answers.yaml" in e.cmd or "notes.md" in e.cmd or "ls -l subagent_live_benchmark/runs" in e.cmd)
            )
            if not is_overhead:
                retrieval_tool_calls += 1
                retrieval_cmd_tokens += cmd_tok
                retrieval_out_tokens += out_tok

        answer_tokens = sum(len(enc.encode(v)) for v in answers.values())

        exact, mean_recall, answered = score_answers(questions, answers)
        violations = detect_violations(name, entries)

        metrics.append(
            ApproachMetrics(
                name=name,
                tool_calls=len(entries),
                retrieval_tool_calls=retrieval_tool_calls,
                cmd_tokens=cmd_tokens,
                out_tokens=out_tokens,
                io_tokens=cmd_tokens + out_tokens,
                retrieval_cmd_tokens=retrieval_cmd_tokens,
                retrieval_out_tokens=retrieval_out_tokens,
                retrieval_io_tokens=retrieval_cmd_tokens + retrieval_out_tokens,
                answer_tokens=answer_tokens,
                answered=answered,
                exact_match_all=exact,
                mean_must_include_recall=mean_recall,
                violations=violations,
            )
        )

    data = {
        "model_for_tokenizer": model,
        "question_count": len(questions),
        "approaches": [m.__dict__ for m in metrics],
    }
    return data


def render_markdown(data: dict) -> str:
    lines: List[str] = []
    lines.append("# Sub-Agent IATF Efficiency Benchmark")
    lines.append("")
    lines.append(f"- Tokenizer model: `{data['model_for_tokenizer']}`")
    lines.append(f"- Question count: `{data['question_count']}`")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| Approach | Tool Calls | Retrieval Calls | Cmd Tokens | Output Tokens | Tool I/O Tokens | Retrieval I/O Tokens | Answer Tokens | Exact Match (all must_include) | Mean must_include Recall | Violations |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for m in data["approaches"]:
        violations = ", ".join(m["violations"]) if m["violations"] else "none"
        lines.append(
            "| {name} | {tool_calls} | {retrieval_tool_calls} | {cmd_tokens} | {out_tokens} | {io_tokens} | {retrieval_io_tokens} | {answer_tokens} | {exact}/{q} | {recall:.3f} | {violations} |".format(
                name=m["name"],
                tool_calls=m["tool_calls"],
                retrieval_tool_calls=m["retrieval_tool_calls"],
                cmd_tokens=m["cmd_tokens"],
                out_tokens=m["out_tokens"],
                io_tokens=m["io_tokens"],
                retrieval_io_tokens=m["retrieval_io_tokens"],
                answer_tokens=m["answer_tokens"],
                exact=m["exact_match_all"],
                q=data["question_count"],
                recall=m["mean_must_include_recall"],
                violations=violations,
            )
        )

    # Efficiency view: tokens per exact match
    lines.append("")
    lines.append("## Efficiency")
    lines.append("")
    lines.append("| Approach | Tool I/O Tokens per Exact-Match Question | Retrieval I/O Tokens per Exact-Match Question |")
    lines.append("|---|---:|---:|")
    for m in data["approaches"]:
        exact = m["exact_match_all"]
        if exact > 0:
            all_value = m["io_tokens"] / exact
            retrieval_value = m["retrieval_io_tokens"] / exact
            lines.append(f"| {m['name']} | {all_value:.2f} | {retrieval_value:.2f} |")
        else:
            lines.append(f"| {m['name']} | inf | inf |")

    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="subagent_live_benchmark", help="benchmark root")
    ap.add_argument("--model", default="gpt-5", help="tokenizer model name")
    ap.add_argument("--json-out", default="subagent_live_benchmark/results/metrics.json")
    ap.add_argument("--md-out", default="subagent_live_benchmark/results/report.md")
    args = ap.parse_args()

    root = Path(args.root)
    data = analyze(root, args.model)

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    md_out.write_text(render_markdown(data), encoding="utf-8")

    print(f"wrote {json_out}")
    print(f"wrote {md_out}")


if __name__ == "__main__":
    main()
