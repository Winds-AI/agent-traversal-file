from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console

from .models import QuestionResult


def save_results(
    console: Console,
    results: List[QuestionResult],
    summary: Dict[str, Any],
    output_dir: Path,
    model: str,
) -> Path:
    """Save results to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"benchmark_{timestamp}.json"

    output_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "total_questions": len(results),
        },
        "summary": summary,
        "results": [asdict(r) for r in results],
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2, default=str)

    console.print(f"\n[green]Results saved to: {output_file}[/green]")
    return output_file

