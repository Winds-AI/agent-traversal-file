from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table

from .models import QuestionResult


def _safe_avg(values: List[float]) -> float:
    """Compute average, returning 0.0 for empty lists."""
    return sum(values) / len(values) if values else 0.0


def summarize_results(results: List[QuestionResult]) -> Dict[str, Any]:
    """Generate summary statistics from results."""
    by_approach: dict[str, list[QuestionResult]] = defaultdict(list)
    for r in results:
        by_approach[r.approach].append(r)

    all_question_ids = {r.question_id for r in results}
    summary: Dict[str, Any] = {"total_questions": len(all_question_ids), "approaches": {}}

    for approach, approach_results in by_approach.items():
        valid = [r for r in approach_results if not r.error]
        errored = [r for r in approach_results if r.error]

        summary["approaches"][approach] = {
            "total": len(approach_results),
            "valid": len(valid),
            "accuracy": _safe_avg([float(r.correct) for r in valid]),
            "avg_score": _safe_avg([r.score for r in valid]),
            "avg_prompt_tokens": _safe_avg([r.prompt_tokens for r in valid]),
            "avg_completion_tokens": _safe_avg([r.completion_tokens for r in valid]),
            "avg_total_tokens": _safe_avg([r.total_tokens for r in valid]),
            "avg_reasoning_tokens": _safe_avg([r.reasoning_tokens for r in valid]),
            "avg_cache_read_tokens": _safe_avg([r.cache_read_tokens for r in valid]),
            "avg_cache_write_tokens": _safe_avg([r.cache_write_tokens for r in valid]),
            "total_cost": sum(r.cost for r in valid),
            "avg_cost": _safe_avg([r.cost for r in valid]),
            "avg_tool_calls": _safe_avg([r.tool_calls for r in valid]),
            "avg_latency_ms": _safe_avg([r.latency_ms for r in valid]),
            "min_latency_ms": min((r.latency_ms for r in valid), default=0.0),
            "max_latency_ms": max((r.latency_ms for r in valid), default=0.0),
            "errors": len(errored),
        }

    by_type: dict[tuple[str, str], list[QuestionResult]] = defaultdict(list)
    for r in results:
        by_type[(r.approach, r.question_type)].append(r)

    summary["by_type"] = {}
    for (approach, qtype), type_results in by_type.items():
        summary["by_type"].setdefault(approach, {})
        valid = [r for r in type_results if not r.error]
        summary["by_type"][approach][qtype] = {
            "count": len(type_results),
            "valid": len(valid),
            "accuracy": _safe_avg([float(r.correct) for r in valid]),
            "avg_score": _safe_avg([r.score for r in valid]),
            "avg_tokens": _safe_avg([r.total_tokens for r in valid]),
            "avg_reasoning_tokens": _safe_avg([r.reasoning_tokens for r in valid]),
            "avg_cache_read_tokens": _safe_avg([r.cache_read_tokens for r in valid]),
            "avg_cache_write_tokens": _safe_avg([r.cache_write_tokens for r in valid]),
            "avg_latency_ms": _safe_avg([r.latency_ms for r in valid]),
            "avg_cost": _safe_avg([r.cost for r in valid]),
            "avg_tool_calls": _safe_avg([r.tool_calls for r in valid]),
            "errors": len([r for r in type_results if r.error]),
        }

    return summary


def print_summary_table(console: Console, summary: Dict[str, Any]) -> None:
    """Print a summary table to console."""
    table = Table(title="Benchmark Results Summary")
    table.add_column("Metric", style="cyan")
    for approach in summary["approaches"]:
        table.add_column(approach.upper(), justify="right")

    metrics = [
        ("Questions", "total", "{}"),
        ("Valid", "valid", "{}"),
        ("Accuracy", "accuracy", "{:.1%}"),
        ("Avg Score", "avg_score", "{:.2f}"),
        ("Avg Tokens", "avg_total_tokens", "{:.0f}"),
        ("Total Cost", "total_cost", "${:.4f}"),
        ("Avg Latency", "avg_latency_ms", "{:.0f}ms"),
        ("Min Latency", "min_latency_ms", "{:.0f}ms"),
        ("Max Latency", "max_latency_ms", "{:.0f}ms"),
        ("Avg Tool Calls", "avg_tool_calls", "{:.1f}"),
        ("Errors", "errors", "{}"),
    ]

    for label, key, fmt in metrics:
        row = [label]
        for approach in summary["approaches"]:
            value = summary["approaches"][approach][key]
            row.append(fmt.format(value))
        table.add_row(*row)

    console.print(table)

    if not summary.get("by_type"):
        return

    type_table = Table(title="Results by Question Type")
    type_table.add_column("Approach", style="cyan")
    type_table.add_column("Type", style="cyan")
    type_table.add_column("Count", justify="right")
    type_table.add_column("Accuracy", justify="right")
    type_table.add_column("Avg Score", justify="right")
    type_table.add_column("Avg Latency", justify="right")
    type_table.add_column("Avg Tokens", justify="right")
    type_table.add_column("Avg Cost", justify="right")

    for approach in sorted(summary["by_type"]):
        for qtype in sorted(summary["by_type"][approach]):
            t = summary["by_type"][approach][qtype]
            type_table.add_row(
                approach,
                qtype,
                str(t["count"]),
                f"{t['accuracy']:.1%}",
                f"{t['avg_score']:.2f}",
                f"{t['avg_latency_ms']:.0f}ms",
                f"{t['avg_tokens']:.0f}",
                f"${t['avg_cost']:.4f}",
            )

    console.print(type_table)
