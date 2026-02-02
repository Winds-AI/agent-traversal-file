#!/usr/bin/env python3
"""
IATF Benchmark Runner

Orchestrates benchmarking across three approaches:
1. Baseline (grep/read)
2. IATF (index-guided navigation)
3. RAG via MCP (vector retrieval)

Uses OpenCode as the agent harness with configurable models.
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from extract_metrics import (
    get_db_path,
    get_latest_session_id,
    extract_session_metrics,
    extract_answer_from_session,
    metrics_to_dict
)
from judge_accuracy import judge_answer, judgment_to_dict


console = Console()


@dataclass
class QuestionResult:
    """Result for a single question."""
    question_id: str
    question_type: str
    question: str
    expected_answer: Any
    approach: str
    model: str
    actual_answer: str
    correct: bool
    score: float
    judgment_reasoning: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    tool_calls: int
    latency_ms: float
    session_id: str
    error: Optional[str] = None


@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""
    opencode_path: str
    db_path: Path
    model: str
    approaches: Dict[str, Any]
    judge_model: str
    judge_temperature: float
    output_dir: Path
    max_retries: int
    retry_delay: int


def load_config(config_path: Path) -> BenchmarkConfig:
    """Load benchmark configuration from YAML."""
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    return BenchmarkConfig(
        opencode_path=cfg["opencode"]["path"],
        db_path=get_db_path(cfg["opencode"]["db_path"]),
        model=f"{cfg['model']['provider']}/{cfg['model']['name']}",
        approaches=cfg["approaches"],
        judge_model=cfg["evaluation"]["judge_model"],
        judge_temperature=cfg["evaluation"]["judge_temperature"],
        output_dir=Path(cfg["output"]["dir"]),
        max_retries=cfg.get("max_retries", 2),
        retry_delay=cfg.get("retry_delay_seconds", 5)
    )


def load_questions(dataset_path: Path) -> List[Dict[str, Any]]:
    """Load questions from YAML file."""
    questions_file = dataset_path / "questions.yaml"
    with open(questions_file) as f:
        data = yaml.safe_load(f)
    return data["questions"]


def load_prompt_template(prompt_path: Path) -> str:
    """Load a prompt template."""
    with open(prompt_path) as f:
        return f.read()


def format_prompt(
    template: str,
    question: str,
    document_path: str
) -> str:
    """Format a prompt template with question and document path."""
    system_prompt = template.format(document_path=document_path)
    return f"{system_prompt}\n\n---\n\nQuestion: {question}\n\nProvide a concise, direct answer."


def run_opencode(
    config: BenchmarkConfig,
    prompt: str,
    working_dir: Path
) -> tuple[str, str, float]:
    """
    Run OpenCode with a prompt and return the result.

    Returns:
        Tuple of (answer, session_id, latency_ms)
    """
    start_time = time.time()

    # Run opencode in non-interactive mode
    cmd = [
        config.opencode_path,
        "-p", prompt,
        "-m", config.model,
        "-f", "json",
        "-q"  # Quiet mode
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        latency_ms = (time.time() - start_time) * 1000

        # Get the session ID (most recent)
        session_id = get_latest_session_id(config.db_path)

        # Extract answer from output or database
        answer = ""
        if result.stdout:
            try:
                output = json.loads(result.stdout)
                answer = output.get("response", output.get("text", result.stdout))
            except json.JSONDecodeError:
                answer = result.stdout.strip()

        # If no answer from stdout, try database
        if not answer and session_id:
            answer = extract_answer_from_session(config.db_path, session_id) or ""

        return answer, session_id or "unknown", latency_ms

    except subprocess.TimeoutExpired:
        latency_ms = (time.time() - start_time) * 1000
        return "ERROR: Timeout", "timeout", latency_ms
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return f"ERROR: {str(e)}", "error", latency_ms


def run_single_question(
    config: BenchmarkConfig,
    question: Dict[str, Any],
    approach: str,
    approach_config: Dict[str, Any],
    dataset_path: Path,
    prompts_dir: Path
) -> QuestionResult:
    """Run a single question through an approach."""

    # Load prompt template
    prompt_template = load_prompt_template(prompts_dir / approach_config["prompt"])

    # Determine document path
    if approach == "rag_mcp":
        document_path = "vector database via MCP"
    else:
        document_path = str(dataset_path / approach_config["document"])

    # Format the full prompt
    full_prompt = format_prompt(
        prompt_template,
        question["question"],
        document_path
    )

    # Run OpenCode
    answer, session_id, latency_ms = run_opencode(
        config,
        full_prompt,
        dataset_path
    )

    # Extract metrics from database
    metrics = None
    if session_id not in ("unknown", "timeout", "error"):
        metrics = extract_session_metrics(config.db_path, session_id)

    # Judge accuracy
    judgment = judge_answer(
        question=question["question"],
        expected_answer=question["answer"],
        actual_answer=answer,
        model=config.judge_model,
        temperature=config.judge_temperature
    )

    return QuestionResult(
        question_id=question["id"],
        question_type=question["type"],
        question=question["question"],
        expected_answer=question["answer"],
        approach=approach,
        model=config.model,
        actual_answer=answer,
        correct=judgment.correct,
        score=judgment.score,
        judgment_reasoning=judgment.reasoning,
        prompt_tokens=metrics.prompt_tokens if metrics else 0,
        completion_tokens=metrics.completion_tokens if metrics else 0,
        total_tokens=metrics.total_tokens if metrics else 0,
        cost=metrics.cost if metrics else 0.0,
        tool_calls=metrics.tool_calls if metrics else 0,
        latency_ms=latency_ms,
        session_id=session_id,
        error=None if not answer.startswith("ERROR:") else answer
    )


def run_benchmark(
    config: BenchmarkConfig,
    dataset_path: Path,
    prompts_dir: Path,
    approaches: Optional[List[str]] = None,
    question_types: Optional[List[str]] = None
) -> List[QuestionResult]:
    """Run the full benchmark."""

    questions = load_questions(dataset_path)

    # Filter by question type if specified
    if question_types:
        questions = [q for q in questions if q["type"] in question_types]

    # Filter approaches
    if approaches:
        active_approaches = {k: v for k, v in config.approaches.items() if k in approaches}
    else:
        active_approaches = {k: v for k, v in config.approaches.items() if v.get("enabled", True)}

    results = []
    total_runs = len(questions) * len(active_approaches)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("Running benchmark...", total=total_runs)

        for question in questions:
            for approach, approach_config in active_approaches.items():
                progress.update(
                    task,
                    description=f"[{approach}] {question['id']}"
                )

                # Retry logic
                for attempt in range(config.max_retries + 1):
                    try:
                        result = run_single_question(
                            config,
                            question,
                            approach,
                            approach_config,
                            dataset_path,
                            prompts_dir
                        )
                        results.append(result)
                        break
                    except Exception as e:
                        if attempt < config.max_retries:
                            console.print(f"[yellow]Retry {attempt + 1} for {question['id']}[/yellow]")
                            time.sleep(config.retry_delay)
                        else:
                            # Record error result
                            results.append(QuestionResult(
                                question_id=question["id"],
                                question_type=question["type"],
                                question=question["question"],
                                expected_answer=question["answer"],
                                approach=approach,
                                model=config.model,
                                actual_answer="",
                                correct=False,
                                score=0.0,
                                judgment_reasoning=f"Error: {str(e)}",
                                prompt_tokens=0,
                                completion_tokens=0,
                                total_tokens=0,
                                cost=0.0,
                                tool_calls=0,
                                latency_ms=0.0,
                                session_id="error",
                                error=str(e)
                            ))

                progress.advance(task)

    return results


def summarize_results(results: List[QuestionResult]) -> Dict[str, Any]:
    """Generate summary statistics from results."""

    # Group by approach
    by_approach = {}
    for r in results:
        if r.approach not in by_approach:
            by_approach[r.approach] = []
        by_approach[r.approach].append(r)

    summary = {
        "total_questions": len(results) // len(by_approach) if by_approach else 0,
        "approaches": {}
    }

    for approach, approach_results in by_approach.items():
        valid_results = [r for r in approach_results if not r.error]

        summary["approaches"][approach] = {
            "accuracy": sum(r.correct for r in valid_results) / len(valid_results) if valid_results else 0,
            "avg_score": sum(r.score for r in valid_results) / len(valid_results) if valid_results else 0,
            "avg_prompt_tokens": sum(r.prompt_tokens for r in valid_results) / len(valid_results) if valid_results else 0,
            "avg_completion_tokens": sum(r.completion_tokens for r in valid_results) / len(valid_results) if valid_results else 0,
            "avg_total_tokens": sum(r.total_tokens for r in valid_results) / len(valid_results) if valid_results else 0,
            "total_cost": sum(r.cost for r in valid_results),
            "avg_cost": sum(r.cost for r in valid_results) / len(valid_results) if valid_results else 0,
            "avg_tool_calls": sum(r.tool_calls for r in valid_results) / len(valid_results) if valid_results else 0,
            "avg_latency_ms": sum(r.latency_ms for r in valid_results) / len(valid_results) if valid_results else 0,
            "errors": len([r for r in approach_results if r.error])
        }

    # By question type
    by_type = {}
    for r in results:
        key = (r.approach, r.question_type)
        if key not in by_type:
            by_type[key] = []
        by_type[key].append(r)

    summary["by_type"] = {}
    for (approach, qtype), type_results in by_type.items():
        if approach not in summary["by_type"]:
            summary["by_type"][approach] = {}
        valid_results = [r for r in type_results if not r.error]
        summary["by_type"][approach][qtype] = {
            "accuracy": sum(r.correct for r in valid_results) / len(valid_results) if valid_results else 0,
            "avg_tokens": sum(r.total_tokens for r in valid_results) / len(valid_results) if valid_results else 0,
            "count": len(valid_results)
        }

    return summary


def print_summary_table(summary: Dict[str, Any]):
    """Print a summary table to console."""
    table = Table(title="Benchmark Results Summary")

    table.add_column("Metric", style="cyan")
    for approach in summary["approaches"]:
        table.add_column(approach.upper(), justify="right")

    metrics = [
        ("Accuracy", "accuracy", "{:.1%}"),
        ("Avg Score", "avg_score", "{:.2f}"),
        ("Avg Tokens", "avg_total_tokens", "{:.0f}"),
        ("Total Cost", "total_cost", "${:.4f}"),
        ("Avg Latency", "avg_latency_ms", "{:.0f}ms"),
        ("Avg Tool Calls", "avg_tool_calls", "{:.1f}"),
        ("Errors", "errors", "{}")
    ]

    for label, key, fmt in metrics:
        row = [label]
        for approach in summary["approaches"]:
            value = summary["approaches"][approach][key]
            row.append(fmt.format(value))
        table.add_row(*row)

    console.print(table)


def save_results(
    results: List[QuestionResult],
    summary: Dict[str, Any],
    output_dir: Path,
    model: str
):
    """Save results to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"benchmark_{timestamp}.json"

    output_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "total_questions": len(results)
        },
        "summary": summary,
        "results": [asdict(r) for r in results]
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2, default=str)

    console.print(f"\n[green]Results saved to: {output_file}[/green]")
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="IATF Benchmark Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to config.yaml"
    )
    parser.add_argument(
        "--dataset", "-d",
        default="bandar_frd",
        help="Dataset name (subdirectory of datasets/)"
    )
    parser.add_argument(
        "--approach", "-a",
        action="append",
        help="Run specific approach(es) only"
    )
    parser.add_argument(
        "--type", "-t",
        action="append",
        help="Run specific question type(s) only"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without executing"
    )

    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent
    benchmark_dir = script_dir.parent
    config_path = benchmark_dir / args.config
    dataset_path = benchmark_dir / "datasets" / args.dataset
    prompts_dir = benchmark_dir / "prompts"

    # Load configuration
    console.print(f"[blue]Loading config from {config_path}[/blue]")
    config = load_config(config_path)

    # Validate dataset exists
    if not dataset_path.exists():
        console.print(f"[red]Dataset not found: {dataset_path}[/red]")
        sys.exit(1)

    # Load and show questions
    questions = load_questions(dataset_path)
    if args.type:
        questions = [q for q in questions if q["type"] in args.type]

    console.print(f"\n[bold]Benchmark Configuration[/bold]")
    console.print(f"  Model: {config.model}")
    console.print(f"  Dataset: {args.dataset}")
    console.print(f"  Questions: {len(questions)}")
    console.print(f"  Approaches: {list(config.approaches.keys())}")

    if args.dry_run:
        console.print("\n[yellow]Dry run - no tests executed[/yellow]")
        return

    # Run benchmark
    console.print("\n[bold]Starting benchmark...[/bold]\n")

    results = run_benchmark(
        config,
        dataset_path,
        prompts_dir,
        approaches=args.approach,
        question_types=args.type
    )

    # Generate summary
    summary = summarize_results(results)

    # Display results
    console.print("\n")
    print_summary_table(summary)

    # Save results
    save_results(results, summary, config.output_dir, config.model)


if __name__ == "__main__":
    main()
