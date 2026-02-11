from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def calculate_line_counts(content: str) -> Dict[str, tuple[int, int, int]]:
    """
    Calculate line ranges for each section in the content.
    Returns dict mapping section_id to (start_line, end_line, word_count).
    """
    lines = content.split("\n")
    sections: dict[str, tuple[int, int, int]] = {}
    current_section: str | None = None
    section_start = 0

    for i, line in enumerate(lines):
        if line.startswith("{#") and not line.startswith("{/"):
            section_id = line[2 : line.index("}")]
            current_section = section_id
            section_start = i + 1  # 1-indexed
        elif line.startswith("{/") and current_section:
            section_end = i + 1  # 1-indexed
            section_lines = lines[section_start - 1 : section_end]
            word_count = sum(len(ln.split()) for ln in section_lines)
            sections[current_section] = (section_start, section_end, word_count)
            current_section = None

    return sections


def format_percentage(value: float) -> str:
    return f"{value * 100:.1f}%"


def format_currency(value: float) -> str:
    return f"${value:.4f}"


def generate_summary_section(summary: Dict[str, Any], model: str) -> str:
    approaches = summary.get("approaches", {})

    table_rows: list[str] = []
    metrics = [
        ("Accuracy", "accuracy", format_percentage),
        ("Avg Score", "avg_score", lambda x: f"{x:.2f}"),
        ("Avg Tokens", "avg_total_tokens", lambda x: f"{int(x):,}"),
        ("Total Cost", "total_cost", format_currency),
        ("Avg Latency", "avg_latency_ms", lambda x: f"{int(x)}ms"),
        ("Avg Tool Calls", "avg_tool_calls", lambda x: f"{x:.1f}"),
        ("Errors", "errors", str),
    ]

    header = "| Metric |"
    separator = "|--------|"
    for approach in approaches:
        header += f" {approach.upper()} |"
        separator += "-------:|"

    table_rows.append(header)
    table_rows.append(separator)

    for label, key, formatter in metrics:
        row = f"| {label} |"
        for approach_data in approaches.values():
            value = approach_data.get(key, 0)
            row += f" {formatter(value)} |"
        table_rows.append(row)

    table = "\n".join(table_rows)

    findings: list[str] = []
    if len(approaches) >= 2:
        baseline_tokens = approaches.get("baseline", {}).get("avg_total_tokens", 0)
        iatf_tokens = approaches.get("iatf", {}).get("avg_total_tokens", 0)
        if baseline_tokens > 0 and iatf_tokens > 0:
            token_reduction = (baseline_tokens - iatf_tokens) / baseline_tokens * 100
            if token_reduction > 0:
                findings.append(
                    f"- IATF reduced token usage by {token_reduction:.1f}% compared to baseline"
                )

        baseline_acc = approaches.get("baseline", {}).get("accuracy", 0)
        iatf_acc = approaches.get("iatf", {}).get("accuracy", 0)
        findings.append(
            f"- Baseline accuracy: {format_percentage(baseline_acc)}, IATF accuracy: {format_percentage(iatf_acc)}"
        )

        baseline_cost = approaches.get("baseline", {}).get("total_cost", 0)
        iatf_cost = approaches.get("iatf", {}).get("total_cost", 0)
        if baseline_cost > 0:
            cost_diff = (baseline_cost - iatf_cost) / baseline_cost * 100
            findings.append(
                f"- Cost difference: {cost_diff:.1f}% {'savings' if cost_diff > 0 else 'increase'} with IATF"
            )

    findings_text = "\n".join(findings) if findings else "- Results pending analysis"

    return f"""# Summary

**Model:** {model}
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Comparison Table

{table}

## Key Findings

{findings_text}
"""


def generate_approach_section(
    approach: str, data: Dict[str, Any], results: List[Dict[str, Any]]
) -> str:
    approach_results = [r for r in results if r.get("approach") == approach]

    by_type: dict[str, list[dict[str, Any]]] = {}
    for r in approach_results:
        qtype = r.get("question_type", "unknown")
        by_type.setdefault(qtype, []).append(r)

    type_breakdown: list[str] = []
    for qtype, type_results in by_type.items():
        correct = sum(1 for r in type_results if r.get("correct"))
        total = len(type_results)
        pct = (correct / total * 100) if total else 0.0
        type_breakdown.append(f"- {qtype}: {correct}/{total} correct ({pct:.0f}%)")

    type_text = "\n".join(type_breakdown) if type_breakdown else "- No results"

    wrong = [r for r in approach_results if not r.get("correct")][:3]
    wrong_samples: list[str] = []
    for r in wrong:
        wrong_samples.append(
            f"""
**Q:** {r.get('question', 'N/A')}
**Expected:** {r.get('expected_answer', 'N/A')}
**Got:** {str(r.get('actual_answer', 'N/A'))[:200]}...
**Reason:** {r.get('judgment_reasoning', 'N/A')}
"""
        )

    wrong_text = "\n".join(wrong_samples) if wrong_samples else "All answers correct!"

    return f"""# {approach.upper()} Results

## Metrics

- **Accuracy:** {format_percentage(data.get('accuracy', 0))}
- **Average Score:** {data.get('avg_score', 0):.2f}
- **Average Tokens:** {int(data.get('avg_total_tokens', 0)):,}
- **Total Cost:** {format_currency(data.get('total_cost', 0))}
- **Average Latency:** {int(data.get('avg_latency_ms', 0))}ms
- **Average Tool Calls:** {data.get('avg_tool_calls', 0):.1f}

## By Question Type

{type_text}

## Sample Incorrect Answers

{wrong_text}
"""


def generate_by_type_section(summary: Dict[str, Any]) -> str:
    by_type = summary.get("by_type", {})
    if not by_type:
        return "# By Question Type\n\nNo type breakdown available."

    all_types: set[str] = set()
    for approach_types in by_type.values():
        all_types.update(approach_types.keys())

    sections: list[str] = []
    for qtype in sorted(all_types):
        type_data: list[str] = []
        for approach, approach_types in by_type.items():
            if qtype not in approach_types:
                continue
            data = approach_types[qtype]
            type_data.append(
                f"- **{approach.upper()}:** {format_percentage(data['accuracy'])} accuracy, {int(data['avg_tokens']):,} avg tokens"
            )
        sections.append(f"## {qtype.title()} Questions\n\n" + "\n".join(type_data) + "\n")

    return "# By Question Type\n\n" + "\n".join(sections)


def generate_raw_data_section(results: List[Dict[str, Any]]) -> str:
    rows = [
        "| ID | Type | Approach | Correct | Score | Tokens | Cost |",
        "|-----|------|----------|---------|-------|--------|------|",
    ]

    for r in results:
        correct = "Yes" if r.get("correct") else "No"
        rows.append(
            f"| {r.get('question_id', 'N/A')} | "
            f"{r.get('question_type', 'N/A')} | "
            f"{r.get('approach', 'N/A')} | "
            f"{correct} | "
            f"{r.get('score', 0):.2f} | "
            f"{r.get('total_tokens', 0):,} | "
            f"{format_currency(r.get('cost', 0))} |"
        )

    return "# Raw Data\n\n" + "\n".join(rows)


def _count_lines(text: str) -> int:
    if not text:
        return 0
    return len(text.split("\n"))


def generate_iatf_report(json_path: Path, output_path: Path) -> None:
    with open(json_path) as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    summary = data.get("summary", {})
    results = data.get("results", [])

    model = metadata.get("model", "unknown")
    dataset = metadata.get("dataset", "unknown")
    timestamp = metadata.get("timestamp", datetime.now().isoformat())

    summary_content = generate_summary_section(summary, model)

    approach_sections: list[tuple[str, str]] = []
    for approach, approach_data in summary.get("approaches", {}).items():
        approach_sections.append(
            (approach, generate_approach_section(approach, approach_data, results))
        )

    by_type_content = generate_by_type_section(summary)
    raw_data_content = generate_raw_data_section(results)

    content_parts: list[str] = []
    content_parts.append(
        "\n{#summary}\n@summary: Overall benchmark comparison\n"
        + summary_content
        + "{/summary}\n"
    )

    for approach, content in approach_sections:
        content_parts.append(
            f"\n{{#{approach}}}\n@summary: {approach.upper()} approach results\n{content}{{/{approach}}}\n"
        )

    content_parts.append(
        "\n{#by-type}\n@summary: Results by question type\n" + by_type_content + "{/by-type}\n"
    )
    content_parts.append(
        "\n{#raw}\n@summary: Per-question raw data\n" + raw_data_content + "{/raw}\n"
    )

    content_section = "\n".join(content_parts)
    line_counts = calculate_line_counts(content_section)

    def adjust_lines(section_id: str, offset: int) -> str:
        if section_id not in line_counts:
            return "lines:TBD | words:TBD"
        start, end, words = line_counts[section_id]
        return f"lines:{start + offset}-{end + offset} | words:{words}"

    # Build INDEX first with placeholder offsets; then compute exact prefix line count and render final INDEX.
    def build_index(offset: int) -> str:
        entries: list[str] = [
            f"# Summary {{#summary | {adjust_lines('summary', offset)}}}",
            "> Key metrics comparison across approaches",
            "",
        ]
        for approach, _ in approach_sections:
            entries.extend(
                [
                    f"# {approach.upper()} Results {{#{approach} | {adjust_lines(approach, offset)}}}",
                    f"> {approach.upper()} approach detailed results",
                    "",
                ]
            )
        entries.extend(
            [
                f"# By Question Type {{#by-type | {adjust_lines('by-type', offset)}}}",
                "> Results broken down by needle/multihop/aggregation",
                "",
                f"# Raw Data {{#raw | {adjust_lines('raw', offset)}}}",
                "> Per-question detailed results",
            ]
        )
        return "\n".join(entries)

    # Header up to INDEX marker (stable)
    header = f""":::IATF
@title: IATF Benchmark Results
@date: {timestamp[:10]}
@model: {model}
@dataset: {dataset}
@generated: {datetime.now().isoformat()}

===INDEX===
<!-- AUTO-GENERATED -->
"""

    # Compute exact line offset: lines before content_section begins.
    index_tmp = build_index(0)
    prefix_tmp = header + "\n\n" + index_tmp + "\n\n===CONTENT===\n"
    offset = _count_lines(prefix_tmp)
    index_section = build_index(offset)

    report = header + "\n\n" + index_section + "\n\n===CONTENT===\n" + content_section + "\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)

    print(f"Report generated: {output_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate IATF-format benchmark report")
    parser.add_argument("--input", "-i", required=True, help="Input JSON file from run_benchmark.py")
    parser.add_argument("--output", "-o", help="Output IATF file (default: results/<timestamp>.iatf)")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1

    if args.output:
        output_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path("results") / f"report_{ts}.iatf"

    generate_iatf_report(input_path, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
