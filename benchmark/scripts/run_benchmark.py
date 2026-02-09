#!/usr/bin/env python3
"""
IATF Benchmark Runner (CLI wrapper).

Implementation lives in benchmark/benchlib/* to keep this entrypoint thin.
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

from dotenv import load_dotenv

# Load .env from benchmark directory (parent of scripts/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Ensure benchlib is importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from benchlib.config import load_config, load_questions
from benchlib.runner import run_benchmark
from benchlib.summary import summarize_results, print_summary_table
from benchlib.results_io import save_results
from benchlib.rag_server import start_rag_server, wait_for_rag_server, stop_rag_server


console = Console()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="IATF Benchmark Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", "-c", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--dataset", "-d", default="bandar_frd", help="Dataset name (subdirectory of datasets/)")
    parser.add_argument("--approach", "-a", action="append", help="Run specific approach(es) only")
    parser.add_argument("--type", "-t", action="append", help="Run specific question type(s) only")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    args = parser.parse_args(argv)

    script_dir = Path(__file__).parent
    benchmark_dir = script_dir.parent
    config_path = benchmark_dir / args.config
    dataset_path = benchmark_dir / "datasets" / args.dataset
    prompts_dir = benchmark_dir / "prompts"

    console.print(f"[blue]Loading config from {config_path}[/blue]")
    config = load_config(config_path)

    if not dataset_path.exists():
        console.print(f"[red]Dataset not found: {dataset_path}[/red]")
        return 1

    questions = load_questions(dataset_path)
    if args.type:
        questions = [q for q in questions if q["type"] in args.type]

    console.print("\n[bold]Benchmark Configuration[/bold]")
    console.print(f"  Model: {config.model}")
    console.print(f"  Dataset: {args.dataset}")
    console.print(f"  Questions: {len(questions)}")
    console.print(f"  Approaches: {list(config.approaches.keys())}")

    if args.dry_run:
        console.print("\n[yellow]Dry run - no tests executed[/yellow]")
        return 0

    if args.approach:
        rag_enabled = "rag_mcp" in args.approach
    else:
        rag_enabled = config.approaches.get("rag_mcp", {}).get("enabled", False)

    rag_proc = None
    if rag_enabled:
        rag_proc = start_rag_server(console, benchmark_dir)
        if not wait_for_rag_server(console, rag_proc):
            console.print("[red]Failed to start RAG server. Aborting.[/red]")
            stop_rag_server(console, rag_proc)
            return 1

    try:
        console.print("\n[bold]Starting benchmark...[/bold]\n")
        results = run_benchmark(
            console,
            config,
            questions,
            dataset_path,
            prompts_dir,
            approaches=args.approach,
            question_types=args.type,
        )

        summary = summarize_results(results)
        console.print("\n")
        print_summary_table(console, summary)
        save_results(console, results, summary, config.output_dir, config.model)
        return 0
    finally:
        if rag_proc:
            stop_rag_server(console, rag_proc)


if __name__ == "__main__":
    raise SystemExit(main())
