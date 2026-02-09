#!/usr/bin/env python3
"""
LLM-based answer accuracy evaluation (CLI wrapper).

Implementation lives in benchmark/benchlib/judge.py.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchlib.judge import judge_answer, judgment_to_dict


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Judge answer accuracy")
    parser.add_argument("--question", "-q", required=True, help="The question")
    parser.add_argument("--expected", "-e", required=True, help="Expected answer")
    parser.add_argument("--actual", "-a", required=True, help="Actual answer to judge")
    parser.add_argument("--model", "-m", default="gpt-4o-mini", help="Judge model")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args(argv)

    result = judge_answer(
        question=args.question,
        expected_answer=args.expected,
        actual_answer=args.actual,
        model=args.model,
    )

    if args.json:
        print(json.dumps(judgment_to_dict(result), indent=2))
    else:
        print(f"Correct: {result.correct}")
        print(f"Score: {result.score:.2f}")
        print(f"Partial credit: {result.partial_credit}")
        print(f"Reasoning: {result.reasoning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

