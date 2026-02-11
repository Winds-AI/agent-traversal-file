#!/usr/bin/env python3
"""
Extract metrics from OpenCode's SQLite database (CLI wrapper).

Implementation lives in benchmark/benchlib/extract_metrics.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchlib.extract_metrics import (  # noqa: F401
    SessionMetrics,
    get_db_path,
    get_latest_session_id,
    extract_session_metrics,
    get_sessions_in_timerange,
    extract_answer_from_session,
    metrics_to_dict,
)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Extract metrics from OpenCode database")
    parser.add_argument("--db", help="Path to opencode.db")
    parser.add_argument("--session", help="Session ID (default: latest)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args(argv)

    db_path = get_db_path(args.db)
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    session_id = args.session or get_latest_session_id(db_path)
    if not session_id:
        print("No sessions found in database")
        return 1

    metrics = extract_session_metrics(db_path, session_id)
    if not metrics:
        print(f"Session not found: {session_id}")
        return 1

    if args.json:
        print(json.dumps(metrics_to_dict(metrics), indent=2))
    else:
        print(f"Session: {metrics.session_id}")
        print(f"Model: {metrics.model}")
        print(f"Tokens: {metrics.total_tokens} (prompt={metrics.prompt_tokens}, completion={metrics.completion_tokens})")
        print(f"Cost: ${metrics.cost:.4f}")
        print(f"Tool calls: {metrics.tool_calls}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

