from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI


@dataclass
class JudgmentResult:
    """Result of accuracy judgment."""

    correct: bool
    score: float  # 0.0 to 1.0
    reasoning: str
    partial_credit: bool  # True if partially correct


JUDGE_SYSTEM_PROMPT = """You are an impartial judge evaluating answer accuracy.

Compare the ACTUAL answer to the EXPECTED answer for the given question.
Consider:
1. Semantic equivalence (different wording, same meaning = correct)
2. Completeness (missing key points = partial)
3. Accuracy (wrong information = incorrect)
4. "Information not found" responses (only correct if answer truly isn't in the source)

Respond in JSON format:
{
    "correct": true/false,
    "score": 0.0-1.0,
    "partial_credit": true/false,
    "reasoning": "Brief explanation"
}

Score guide:
- 1.0: Fully correct, complete answer
- 0.7-0.9: Mostly correct, minor omissions
- 0.4-0.6: Partially correct, significant gaps
- 0.1-0.3: Mostly wrong, some relevant info
- 0.0: Completely wrong or irrelevant
"""


def create_judge_prompt(
    question: str,
    expected_answer: Any,
    actual_answer: str,
    answer_type: str = "text",
) -> str:
    """Create the prompt for the judge LLM."""
    if isinstance(expected_answer, list):
        expected_formatted = "\n".join(f"- {item}" for item in expected_answer)
    else:
        expected_formatted = str(expected_answer)

    return f"""QUESTION:
{question}

EXPECTED ANSWER:
{expected_formatted}

ACTUAL ANSWER:
{actual_answer}

Judge the accuracy of the ACTUAL answer compared to the EXPECTED answer.
For list-type answers, check if all items are present (order doesn't matter).
"""


def judge_answer(
    question: str,
    expected_answer: Any,
    actual_answer: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
    api_key: Optional[str] = None,
) -> JudgmentResult:
    """Use an LLM to judge if the actual answer is correct."""
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    judge_prompt = create_judge_prompt(question, expected_answer, actual_answer)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": judge_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return JudgmentResult(
            correct=result.get("correct", False),
            score=float(result.get("score", 0.0)),
            reasoning=result.get("reasoning", "No reasoning provided"),
            partial_credit=result.get("partial_credit", False),
        )
    except Exception as e:
        raise RuntimeError(f"Judge API call failed: {e}") from e


def judge_batch(
    evaluations: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
) -> List[JudgmentResult]:
    """Judge multiple answers in batch."""
    results: list[JudgmentResult] = []
    for eval_item in evaluations:
        results.append(
            judge_answer(
                question=eval_item["question"],
                expected_answer=eval_item["expected"],
                actual_answer=eval_item["actual"],
                model=model,
                temperature=temperature,
            )
        )
    return results


def judgment_to_dict(judgment: JudgmentResult) -> Dict[str, Any]:
    """Convert JudgmentResult to dictionary for JSON serialization."""
    return {
        "correct": judgment.correct,
        "score": judgment.score,
        "partial_credit": judgment.partial_credit,
        "reasoning": judgment.reasoning,
    }

