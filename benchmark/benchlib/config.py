from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from .extract_metrics import get_db_path
from .models import BenchmarkConfig


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
        retry_delay=cfg.get("retry_delay_seconds", 5),
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


def format_prompt(template: str, question: str, document_path: str) -> str:
    """Format a prompt template with question and document path."""
    system_prompt = template.format(document_path=document_path)
    return f"{system_prompt}\n\n---\n\nQuestion: {question}\n\nProvide a concise, direct answer."

