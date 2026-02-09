from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from rich.console import Console


def save_session_export(
    console: Console,
    run_result: Dict[str, Any],
    question: Dict[str, Any],
    approach: str,
    model: str,
    prompt: str,
    output_dir: Path,
) -> Path:
    """
    Save the full opencode session to a JSON file, including every tool call
    with its name, arguments, and result.
    """
    sessions_dir = output_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{question['id']}_{approach}_{timestamp}.json"

    export = {
        "metadata": {
            "question_id": question["id"],
            "question_type": question["type"],
            "approach": approach,
            "model": model,
            "session_id": run_result.get("session_id", "unknown"),
            "timestamp": now.isoformat(),
        },
        "prompt": prompt,
        "question": question["question"],
        "expected_answer": question["answer"],
        "actual_answer": run_result.get("answer", ""),
        "metrics": {
            "prompt_tokens": run_result.get("prompt_tokens", 0),
            "completion_tokens": run_result.get("completion_tokens", 0),
            "total_tokens": run_result.get("total_tokens", 0),
            "reasoning_tokens": run_result.get("reasoning_tokens", 0),
            "cache_read_tokens": run_result.get("cache_read_tokens", 0),
            "cache_write_tokens": run_result.get("cache_write_tokens", 0),
            "cost": run_result.get("cost", 0.0),
            "latency_ms": run_result.get("latency_ms", 0.0),
            "tool_calls_count": run_result.get("tool_calls", 0),
        },
        "tool_calls": run_result.get("tool_call_details", []),
        "raw_events": run_result.get("raw_events", []),
        "error": run_result.get("error"),
    }

    export_path = sessions_dir / filename
    with open(export_path, "w") as f:
        json.dump(export, f, indent=2, default=str)

    console.print(f"  [dim]Session exported: {export_path}[/dim]")
    return export_path
