from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchlib.models import BenchmarkConfig, OpenCodeRun
from benchlib.opencode_runner import prepare_opencode_isolation, run_opencode
from benchlib.runner import run_benchmark, run_single_question


def _make_config(output_dir: Path, db_path: Path | None = None) -> BenchmarkConfig:
    return BenchmarkConfig(
        opencode_path="opencode",
        db_path=db_path or (output_dir / "opencode.db"),
        model="opencode/test-model",
        approaches={
            "baseline": {
                "enabled": True,
                "prompt": "baseline.md",
                "document": "document.txt",
            }
        },
        judge_model="gpt-5-mini",
        judge_temperature=0.0,
        output_dir=output_dir,
        max_retries=0,
        retry_delay=0,
    )


class BenchmarkRobustnessTests(unittest.TestCase):
    def test_run_opencode_nonzero_exit_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = _make_config(root)
            completed = subprocess.CompletedProcess(
                args=["opencode", "run"],
                returncode=2,
                stdout="",
                stderr="network failed",
            )

            with patch("benchlib.opencode_runner.subprocess.run", return_value=completed):
                result = run_opencode(
                    Console(),
                    config,
                    prompt="test prompt",
                    working_dir=root,
                )

            self.assertIsNotNone(result.error)
            self.assertIn("code 2", result.error or "")
            self.assertTrue(result.answer.startswith("ERROR: opencode exited"))
            self.assertEqual(result.session_id, "unknown")

    def test_run_opencode_db_fallback_uses_stream_session_id_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db_path = root / "opencode.db"
            db_path.touch()
            config = _make_config(root, db_path=db_path)
            completed = subprocess.CompletedProcess(
                args=["opencode", "run"],
                returncode=0,
                stdout='{"sessionID":"sess-123"}\n',
                stderr="",
            )

            with patch("benchlib.opencode_runner.subprocess.run", return_value=completed):
                with patch(
                    "benchlib.opencode_runner.extract_answer_from_session",
                    return_value="answer-from-db",
                ) as extract_mock:
                    result = run_opencode(
                        Console(),
                        config,
                        prompt="test prompt",
                        working_dir=root,
                    )

            extract_mock.assert_called_once_with(db_path, "sess-123")
            self.assertEqual(result.answer, "answer-from-db")
            self.assertIsNone(result.error)

    def test_run_single_question_skips_judge_when_run_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dataset_dir = root / "dataset"
            prompts_dir = root / "prompts"
            output_dir = root / "results"
            dataset_dir.mkdir()
            prompts_dir.mkdir()
            output_dir.mkdir()

            (dataset_dir / "document.txt").write_text("dummy", encoding="utf-8")
            (prompts_dir / "baseline.md").write_text(
                "Answer using {document_path}",
                encoding="utf-8",
            )

            config = _make_config(output_dir)
            isolation = prepare_opencode_isolation(
                approach="baseline",
                approach_config={"mcp_enabled": False, "skills_enabled": False},
                run_cwd=dataset_dir,
            )

            question = {
                "id": "q-1",
                "type": "needle",
                "question": "What is X?",
                "answer": "X",
            }

            run_result = OpenCodeRun(
                answer="ERROR: timeout",
                session_id="timeout",
                latency_ms=1.0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                reasoning_tokens=0,
                cache_read_tokens=0,
                cache_write_tokens=0,
                cost=0.0,
                tool_calls=0,
                tool_call_details=[],
                raw_events=[],
                error="ERROR: timeout",
            )

            try:
                with patch("benchlib.runner.run_opencode", return_value=run_result):
                    with patch("benchlib.runner.judge_answer") as judge_mock:
                        result = run_single_question(
                            console=Console(),
                            config=config,
                            question=question,
                            approach="baseline",
                            approach_config={
                                "prompt": "baseline.md",
                                "document": "document.txt",
                            },
                            dataset_path=dataset_dir,
                            prompts_dir=prompts_dir,
                            prompt_template_cache={},
                            isolation=isolation,
                        )
                judge_mock.assert_not_called()
            finally:
                isolation.cleanup()

            self.assertEqual(result.score, -1.0)
            self.assertIn("RUN_ERROR:", result.judgment_reasoning)
            self.assertEqual(result.error, "ERROR: timeout")

    def test_run_benchmark_rejects_unknown_filters(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = _make_config(root)
            questions = [
                {
                    "id": "q-1",
                    "type": "needle",
                    "question": "What is X?",
                    "answer": "X",
                }
            ]

            with self.assertRaisesRegex(ValueError, "Unknown approach"):
                run_benchmark(
                    console=Console(),
                    config=config,
                    questions=questions,
                    dataset_path=root,
                    prompts_dir=root,
                    approach="does_not_exist",
                )

            with self.assertRaisesRegex(ValueError, "Approach must be"):
                run_benchmark(
                    console=Console(),
                    config=config,
                    questions=questions,
                    dataset_path=root,
                    prompts_dir=root,
                    approach="",  # type: ignore[arg-type]
                )

            with self.assertRaisesRegex(ValueError, "Unknown question type"):
                run_benchmark(
                    console=Console(),
                    config=config,
                    questions=questions,
                    dataset_path=root,
                    prompts_dir=root,
                    approach="baseline",
                    question_types=["does_not_exist"],
                )


if __name__ == "__main__":
    unittest.main()
