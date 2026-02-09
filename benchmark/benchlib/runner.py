from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .config import load_prompt_template, format_prompt
from .judge import judge_answer, JudgmentResult
from .models import BenchmarkConfig, QuestionResult
from .opencode_runner import OpenCodeIsolation, prepare_opencode_isolation, run_opencode
from .session_export import save_session_export


def run_single_question(
    console: Console,
    config: BenchmarkConfig,
    question: Dict[str, Any],
    approach: str,
    approach_config: Dict[str, Any],
    dataset_path: Path,
    prompts_dir: Path,
    prompt_template_cache: Dict[Path, str],
    isolation: OpenCodeIsolation,
) -> QuestionResult:
    """Run a single question through an approach."""
    prompt_file = prompts_dir / approach_config["prompt"]
    console.print(f"  [dim]Loading prompt: {prompt_file}[/dim]")
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt template not found: {prompt_file}")

    prompt_template = prompt_template_cache.get(prompt_file)
    if prompt_template is None:
        prompt_template = load_prompt_template(prompt_file)
        prompt_template_cache[prompt_file] = prompt_template

    if approach == "rag_mcp":
        document_path = "vector database via MCP"
    else:
        document_path = str((dataset_path / approach_config["document"]).resolve())

    full_prompt = format_prompt(
        prompt_template,
        question["question"],
        document_path,
    )

    console.print(f"  [dim]Running opencode for {question['id']} ({approach})...[/dim]")
    run_result = run_opencode(
        console,
        config,
        full_prompt,
        dataset_path,
        opencode_cwd=isolation.cwd,
        opencode_env=isolation.env,
    )

    if run_result.error:
        console.print(f"  [red]opencode error: {run_result.error[:200]}[/red]")

    save_session_export(
        console,
        {
            "answer": run_result.answer,
            "session_id": run_result.session_id,
            "latency_ms": run_result.latency_ms,
            "prompt_tokens": run_result.prompt_tokens,
            "completion_tokens": run_result.completion_tokens,
            "total_tokens": run_result.total_tokens,
            "reasoning_tokens": run_result.reasoning_tokens,
            "cache_read_tokens": run_result.cache_read_tokens,
            "cache_write_tokens": run_result.cache_write_tokens,
            "cost": run_result.cost,
            "tool_calls": run_result.tool_calls,
            "tool_call_details": run_result.tool_call_details,
            "raw_events": run_result.raw_events,
            "error": run_result.error,
        },
        question,
        approach,
        config.model,
        full_prompt,
        config.output_dir,
    )

    console.print(f"  [dim]Judging answer (model={config.judge_model})...[/dim]")
    try:
        judgment = judge_answer(
            question=question["question"],
            expected_answer=question["answer"],
            actual_answer=run_result.answer,
            model=config.judge_model,
            temperature=config.judge_temperature,
        )
        console.print(
            f"  [dim]Judgment: correct={judgment.correct}, score={judgment.score}[/dim]"
        )
    except Exception as e:
        console.print(f"  [red]Judge failed: {type(e).__name__}: {e}[/red]")
        console.print(
            "  [yellow]Recording as unjudged (not marking incorrect)[/yellow]"
        )
        judgment = JudgmentResult(
            correct=False,
            score=-1.0,  # -1 signals "not judged"
            reasoning=f"JUDGE_ERROR: {e}",
            partial_credit=False,
        )

        # Preserve prior behavior: stash judge error on the result.
        run_result.error = f"JUDGE_ERROR: {e}"

    return QuestionResult(
        question_id=question["id"],
        question_type=question["type"],
        question=question["question"],
        expected_answer=question["answer"],
        approach=approach,
        model=config.model,
        actual_answer=run_result.answer,
        correct=judgment.correct,
        score=judgment.score,
        judgment_reasoning=judgment.reasoning,
        prompt_tokens=run_result.prompt_tokens,
        completion_tokens=run_result.completion_tokens,
        total_tokens=run_result.total_tokens,
        reasoning_tokens=run_result.reasoning_tokens,
        cache_read_tokens=run_result.cache_read_tokens,
        cache_write_tokens=run_result.cache_write_tokens,
        cost=run_result.cost,
        tool_calls=run_result.tool_calls,
        latency_ms=run_result.latency_ms,
        session_id=run_result.session_id,
        error=run_result.error,
    )


def run_benchmark(
    console: Console,
    config: BenchmarkConfig,
    questions: List[Dict[str, Any]],
    dataset_path: Path,
    prompts_dir: Path,
    approaches: Optional[List[str]] = None,
    question_types: Optional[List[str]] = None,
) -> List[QuestionResult]:
    """Run the full benchmark."""
    active_questions = questions
    if question_types:
        active_questions = [q for q in active_questions if q["type"] in question_types]

    if approaches:
        active_approaches = {
            k: v for k, v in config.approaches.items() if k in approaches
        }
    else:
        active_approaches = {
            k: v for k, v in config.approaches.items() if v.get("enabled", True)
        }

    results: list[QuestionResult] = []
    total_runs = len(active_questions) * len(active_approaches)
    prompt_template_cache: dict[Path, str] = {}

    isolations: dict[str, OpenCodeIsolation] = {}
    try:
        for approach, approach_config in active_approaches.items():
            isolations[approach] = prepare_opencode_isolation(
                approach=approach,
                approach_config=approach_config,
                run_cwd=dataset_path,
            )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("Running benchmark...", total=total_runs)

            for question in active_questions:
                for approach, approach_config in active_approaches.items():
                    progress.update(task, description=f"[{approach}] {question['id']}")

                    # Retry logic with accurate elapsed time on final failure.
                    last_error: Optional[Exception] = None
                    attempt_start = time.time()
                    for attempt in range(config.max_retries + 1):
                        attempt_start = time.time()
                        try:
                            result = run_single_question(
                                console,
                                config,
                                question,
                                approach,
                                approach_config,
                                dataset_path,
                                prompts_dir,
                                prompt_template_cache,
                                isolations[approach],
                            )
                            results.append(result)
                            last_error = None
                            break
                        except Exception as e:
                            last_error = e
                            if attempt < config.max_retries:
                                console.print(
                                    f"[yellow]Retry {attempt + 1} for {question['id']}: {type(e).__name__}: {e}[/yellow]"
                                )
                                time.sleep(config.retry_delay)

                    if last_error is not None:
                        console.print(
                            f"[red]All retries exhausted for {question['id']}: {type(last_error).__name__}: {last_error}[/red]"
                        )
                        latency_ms = (time.time() - attempt_start) * 1000
                        results.append(
                            QuestionResult(
                                question_id=question["id"],
                                question_type=question["type"],
                                question=question["question"],
                                expected_answer=question["answer"],
                                approach=approach,
                                model=config.model,
                                actual_answer="",
                                correct=False,
                                score=0.0,
                                judgment_reasoning=f"Error: {last_error}",
                            prompt_tokens=0,
                            completion_tokens=0,
                            total_tokens=0,
                            reasoning_tokens=0,
                            cache_read_tokens=0,
                            cache_write_tokens=0,
                            cost=0.0,
                            tool_calls=0,
                            latency_ms=latency_ms,
                            session_id="error",
                            error=str(last_error),
                            )
                        )

                    progress.advance(task)

        return results
    finally:
        for isolation in isolations.values():
            isolation.cleanup()
