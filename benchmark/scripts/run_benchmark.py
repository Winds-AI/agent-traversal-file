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
import signal
import subprocess
import tempfile
import argparse
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

import yaml
from dotenv import load_dotenv

# Load .env from benchmark directory (parent of scripts/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

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
from judge_accuracy import judge_answer, judgment_to_dict, JudgmentResult


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


def parse_opencode_json_stream(stdout: str) -> Dict[str, Any]:
    """
    Parse opencode's newline-delimited JSON event stream.

    Extracts session_id, answer text, token counts, cost, tool call count,
    and full tool call details (name, args, result) from the JSON events.

    Returns dict with keys: session_id, answer, prompt_tokens, completion_tokens,
                            total_tokens, cost, tool_calls, tool_call_details, raw_events
    """
    session_id = "unknown"
    text_parts = []
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0.0
    tool_calls = 0
    # Track tool calls: toolCallId -> {name, args, result, state}
    tool_map: Dict[str, Dict[str, Any]] = {}
    raw_events = []

    for line in stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        raw_events.append(event)

        # Extract session ID from any event
        if session_id == "unknown" and "sessionID" in event:
            session_id = event["sessionID"]

        event_type = event.get("type", "")
        part = event.get("part", {})

        # Collect text parts for the answer
        if event_type == "text":
            text = part.get("text", "")
            if text:
                text_parts.append(text)

        # Capture tool calls with full details
        elif event_type == "tool_use":
            tool_call_id = part.get("toolCallId", f"unknown_{tool_calls}")
            tool_name = part.get("toolName", "unknown")
            state = part.get("state", "")
            args = part.get("args", {})
            result = part.get("result", "")

            if tool_call_id not in tool_map:
                tool_map[tool_call_id] = {
                    "toolCallId": tool_call_id,
                    "toolName": tool_name,
                    "args": {},
                    "result": "",
                    "state": state,
                }

            entry = tool_map[tool_call_id]
            if state == "call" or state == "partial-call":
                entry["args"] = args
                entry["toolName"] = tool_name
                tool_calls += 1
            elif state == "result":
                entry["result"] = result
                entry["state"] = "completed"
            else:
                # Any other state, update what we have
                if args:
                    entry["args"] = args
                if result:
                    entry["result"] = result
                if not entry.get("toolName") or entry["toolName"] == "unknown":
                    entry["toolName"] = tool_name
                tool_calls += 1

        # Accumulate tokens and cost from step_finish events
        elif event_type == "step_finish":
            tokens = part.get("tokens", {})
            total_prompt_tokens += tokens.get("input", 0)
            total_completion_tokens += tokens.get("output", 0)
            total_cost += part.get("cost", 0.0)

    return {
        "session_id": session_id,
        "answer": "\n".join(text_parts),
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
        "cost": total_cost,
        "tool_calls": tool_calls,
        "tool_call_details": list(tool_map.values()),
        "raw_events": raw_events,
    }


def run_opencode(
    config: BenchmarkConfig,
    prompt: str,
    working_dir: Path
) -> Dict[str, Any]:
    """
    Run OpenCode with a prompt and return parsed results.

    Returns:
        Dict with keys: answer, session_id, latency_ms, prompt_tokens,
                        completion_tokens, total_tokens, cost, tool_calls, error
    """
    start_time = time.time()

    # Run opencode in non-interactive mode
    cmd = [
        config.opencode_path,
        "run",
        prompt,
        "-m", config.model,
        "--format", "json",
    ]

    try:
        console.print(f"  [dim]Running: {' '.join(cmd[:3])}... (model={config.model})[/dim]")
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        latency_ms = (time.time() - start_time) * 1000

        if result.returncode != 0:
            console.print(f"  [red]opencode exited with code {result.returncode}[/red]")
            if result.stderr:
                console.print(f"  [red]stderr: {result.stderr[:500]}[/red]")
            if result.stdout:
                console.print(f"  [dim]stdout (first 500): {result.stdout[:500]}[/dim]")

        # Parse metrics and answer from JSON event stream
        parsed = parse_opencode_json_stream(result.stdout or "")

        if not parsed["answer"]:
            console.print(f"  [yellow]No answer parsed from JSON stream (session={parsed['session_id']})[/yellow]")
            if result.stdout:
                console.print(f"  [dim]Raw stdout (first 800):\n{result.stdout[:800]}[/dim]")

        # Fallback: if no answer from JSON stream, try the database
        if not parsed["answer"] and parsed["session_id"] != "unknown":
            console.print(f"  [dim]Trying DB fallback for session {parsed['session_id']}...[/dim]")
            parsed["answer"] = extract_answer_from_session(
                config.db_path, parsed["session_id"]
            ) or ""

        # Fallback: if session_id still unknown, try DB for latest
        if parsed["session_id"] == "unknown":
            parsed["session_id"] = get_latest_session_id(config.db_path) or "unknown"

        parsed["latency_ms"] = latency_ms
        parsed["error"] = None

        # Check if answer indicates an error
        if parsed["answer"].startswith("ERROR:"):
            parsed["error"] = parsed["answer"]

        console.print(f"  [dim]Result: session={parsed['session_id']}, tokens={parsed['total_tokens']}, answer_len={len(parsed['answer'])}[/dim]")
        return parsed

    except subprocess.TimeoutExpired:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "answer": "ERROR: Timeout",
            "session_id": "timeout",
            "latency_ms": latency_ms,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
            "tool_calls": 0,
            "error": "ERROR: Timeout",
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "answer": f"ERROR: {str(e)}",
            "session_id": "error",
            "latency_ms": latency_ms,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost": 0.0,
            "tool_calls": 0,
            "error": f"ERROR: {str(e)}",
        }


def save_session_export(
    run_result: Dict[str, Any],
    question: Dict[str, Any],
    approach: str,
    model: str,
    prompt: str,
    output_dir: Path,
):
    """
    Save the full opencode session to a JSON file, including every tool call
    with its name, arguments, and result.
    """
    sessions_dir = output_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{question['id']}_{approach}_{timestamp}.json"

    export = {
        "metadata": {
            "question_id": question["id"],
            "question_type": question["type"],
            "approach": approach,
            "model": model,
            "session_id": run_result.get("session_id", "unknown"),
            "timestamp": datetime.now().isoformat(),
        },
        "prompt": prompt,
        "question": question["question"],
        "expected_answer": question["answer"],
        "actual_answer": run_result.get("answer", ""),
        "metrics": {
            "prompt_tokens": run_result.get("prompt_tokens", 0),
            "completion_tokens": run_result.get("completion_tokens", 0),
            "total_tokens": run_result.get("total_tokens", 0),
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
    prompt_file = prompts_dir / approach_config["prompt"]
    console.print(f"  [dim]Loading prompt: {prompt_file}[/dim]")
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_file}")
    prompt_template = load_prompt_template(prompt_file)

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

    # Run OpenCode and get all metrics from JSON stream
    console.print(f"  [dim]Running opencode for {question['id']} ({approach})...[/dim]")
    run_result = run_opencode(config, full_prompt, dataset_path)

    if run_result.get("error"):
        console.print(f"  [red]opencode error: {run_result['error'][:200]}[/red]")

    # Save full session export (tool calls, args, results, raw events)
    save_session_export(
        run_result, question, approach, config.model,
        full_prompt, config.output_dir,
    )

    # Judge accuracy
    console.print(f"  [dim]Judging answer (model={config.judge_model})...[/dim]")
    try:
        judgment = judge_answer(
            question=question["question"],
            expected_answer=question["answer"],
            actual_answer=run_result["answer"],
            model=config.judge_model,
            temperature=config.judge_temperature
        )
        console.print(f"  [dim]Judgment: correct={judgment.correct}, score={judgment.score}[/dim]")
    except Exception as e:
        console.print(f"  [red]Judge failed: {type(e).__name__}: {e}[/red]")
        console.print(f"  [yellow]Recording as unjudged (not marking incorrect)[/yellow]")
        judgment = JudgmentResult(
            correct=False,
            score=-1.0,  # -1 signals "not judged" vs genuinely incorrect (0.0)
            reasoning=f"JUDGE_ERROR: {e}",
            partial_credit=False,
        )
        run_result["error"] = f"JUDGE_ERROR: {e}"

    return QuestionResult(
        question_id=question["id"],
        question_type=question["type"],
        question=question["question"],
        expected_answer=question["answer"],
        approach=approach,
        model=config.model,
        actual_answer=run_result["answer"],
        correct=judgment.correct,
        score=judgment.score,
        judgment_reasoning=judgment.reasoning,
        prompt_tokens=run_result["prompt_tokens"],
        completion_tokens=run_result["completion_tokens"],
        total_tokens=run_result["total_tokens"],
        cost=run_result["cost"],
        tool_calls=run_result["tool_calls"],
        latency_ms=run_result["latency_ms"],
        session_id=run_result["session_id"],
        error=run_result["error"],
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
                last_error_time = time.time()
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
                        last_error_time = time.time()
                        if attempt < config.max_retries:
                            console.print(f"[yellow]Retry {attempt + 1} for {question['id']}: {type(e).__name__}: {e}[/yellow]")
                            time.sleep(config.retry_delay)
                        else:
                            console.print(f"[red]All retries exhausted for {question['id']}: {type(e).__name__}: {e}[/red]")
                            # Record error result with actual elapsed time
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
                                latency_ms=(last_error_time - last_error_time) * 1000,
                                session_id="error",
                                error=str(e)
                            ))

                progress.advance(task)

    return results


def _safe_avg(values: List[float]) -> float:
    """Compute average, returning 0.0 for empty lists."""
    return sum(values) / len(values) if values else 0.0


def summarize_results(results: List[QuestionResult]) -> Dict[str, Any]:
    """Generate summary statistics from results."""

    # Group by approach
    by_approach: Dict[str, List[QuestionResult]] = {}
    for r in results:
        by_approach.setdefault(r.approach, []).append(r)

    # Count unique questions across all approaches
    all_question_ids = {r.question_id for r in results}

    summary = {
        "total_questions": len(all_question_ids),
        "approaches": {}
    }

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
            "total_cost": sum(r.cost for r in valid),
            "avg_cost": _safe_avg([r.cost for r in valid]),
            "avg_tool_calls": _safe_avg([r.tool_calls for r in valid]),
            "avg_latency_ms": _safe_avg([r.latency_ms for r in valid]),
            "min_latency_ms": min((r.latency_ms for r in valid), default=0.0),
            "max_latency_ms": max((r.latency_ms for r in valid), default=0.0),
            "errors": len(errored),
        }

    # By question type — full metrics per type per approach
    by_type: Dict[tuple, List[QuestionResult]] = {}
    for r in results:
        by_type.setdefault((r.approach, r.question_type), []).append(r)

    summary["by_type"] = {}
    for (approach, qtype), type_results in by_type.items():
        if approach not in summary["by_type"]:
            summary["by_type"][approach] = {}
        valid = [r for r in type_results if not r.error]
        summary["by_type"][approach][qtype] = {
            "count": len(type_results),
            "valid": len(valid),
            "accuracy": _safe_avg([float(r.correct) for r in valid]),
            "avg_score": _safe_avg([r.score for r in valid]),
            "avg_tokens": _safe_avg([r.total_tokens for r in valid]),
            "avg_latency_ms": _safe_avg([r.latency_ms for r in valid]),
            "avg_cost": _safe_avg([r.cost for r in valid]),
            "avg_tool_calls": _safe_avg([r.tool_calls for r in valid]),
            "errors": len([r for r in type_results if r.error]),
        }

    return summary


def print_summary_table(summary: Dict[str, Any]):
    """Print a summary table to console."""
    # Main summary table
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
        ("Errors", "errors", "{}")
    ]

    for label, key, fmt in metrics:
        row = [label]
        for approach in summary["approaches"]:
            value = summary["approaches"][approach][key]
            row.append(fmt.format(value))
        table.add_row(*row)

    console.print(table)

    # Per-type breakdown table
    if summary.get("by_type"):
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


RAG_SERVER_PORT = 8808
RAG_SERVER_READY_MARKER = "Embedding model loaded and ready"


def start_rag_server(benchmark_dir: Path) -> subprocess.Popen:
    """Start the RAG MCP server as a persistent background process."""
    server_script = benchmark_dir / "mcp-rag-server" / "server.py"
    venv_python = benchmark_dir.parent / ".venv" / "bin" / "python3"

    python_cmd = str(venv_python) if venv_python.exists() else "python3"

    cmd = [
        python_cmd,
        str(server_script),
        "--transport", "streamable-http",
        "--port", str(RAG_SERVER_PORT),
    ]

    console.print(f"[blue]Starting RAG MCP server on port {RAG_SERVER_PORT}...[/blue]")

    proc = subprocess.Popen(
        cmd,
        cwd=str(benchmark_dir / "mcp-rag-server"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    return proc


def wait_for_rag_server(proc: subprocess.Popen, timeout: int = 300) -> bool:
    """Wait for the RAG server to be fully ready (model loaded)."""
    start = time.time()

    # First wait for the server process to print the ready marker
    console.print("[yellow]Waiting for embedding model to load (this may take a few minutes on first run)...[/yellow]")

    while time.time() - start < timeout:
        if proc.poll() is not None:
            # Process died
            remaining = proc.stdout.read() if proc.stdout else ""
            console.print(f"[red]RAG server died: {remaining}[/red]")
            return False

        line = proc.stdout.readline()
        if line:
            line = line.strip()
            if RAG_SERVER_READY_MARKER in line:
                console.print(f"[green]RAG server ready![/green]")
                # Give the HTTP server a moment to start accepting connections
                time.sleep(2)
                return True

    console.print(f"[red]RAG server timed out after {timeout}s[/red]")
    return False


def stop_rag_server(proc: subprocess.Popen):
    """Gracefully stop the RAG MCP server."""
    if proc.poll() is None:
        console.print("[blue]Shutting down RAG MCP server...[/blue]")
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        console.print("[green]RAG server stopped.[/green]")


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

    # Determine if RAG approach is active
    if args.approach:
        rag_enabled = "rag_mcp" in args.approach
    else:
        rag_enabled = config.approaches.get("rag_mcp", {}).get("enabled", False)

    # Start RAG MCP server if needed
    rag_proc = None
    if rag_enabled:
        rag_proc = start_rag_server(benchmark_dir)
        if not wait_for_rag_server(rag_proc):
            console.print("[red]Failed to start RAG server. Aborting.[/red]")
            stop_rag_server(rag_proc)
            sys.exit(1)

    try:
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

    finally:
        # Always shut down RAG server when done
        if rag_proc:
            stop_rag_server(rag_proc)


if __name__ == "__main__":
    main()
