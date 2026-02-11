#!/usr/bin/env python3
"""
Strict single-job benchmark entrypoint.

Alias of run_benchmark.py, which now enforces one approach per run
to keep OpenCode environment isolation deterministic.
"""

from __future__ import annotations

from run_benchmark import main


if __name__ == "__main__":
    raise SystemExit(main())
