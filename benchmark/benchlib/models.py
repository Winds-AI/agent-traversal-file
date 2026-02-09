from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Dict


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
    reasoning_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
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


@dataclass
class OpenCodeRun:
    """Parsed result from an OpenCode run."""

    answer: str
    session_id: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    reasoning_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost: float
    tool_calls: int
    tool_call_details: list[dict[str, Any]]
    raw_events: list[dict[str, Any]]
    error: Optional[str]
