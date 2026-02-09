#!/usr/bin/env python3
"""
Generate IATF-format benchmark reports (CLI wrapper).

Implementation lives in benchmark/benchlib/report.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchlib.report import main


if __name__ == "__main__":
    raise SystemExit(main())

