#!/usr/bin/env python3
"""
LLM-based answer accuracy evaluation.

Uses an LLM to judge whether an answer is correct compared to the expected answer,
accounting for paraphrasing, partial matches, and semantic equivalence.
"""

import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
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
    expected_answer: str,
    actual_answer: str,
    answer_type: str = "text"
) -> str:
    """Create the prompt for the judge LLM."""

    # Format expected answer based on type
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
    expected_answer: str,
    actual_answer: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
    api_key: Optional[str] = None
) -> JudgmentResult:
    """
    Use an LLM to judge if the actual answer is correct.

    Args:
        question: The original question
        expected_answer: The expected/correct answer
        actual_answer: The answer to evaluate
        model: OpenAI model to use for judging
        temperature: Temperature for judge model
        api_key: OpenAI API key (uses OPENAI_API_KEY env var if not provided)

    Returns:
        JudgmentResult with correctness evaluation
    """
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    judge_prompt = create_judge_prompt(question, expected_answer, actual_answer)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": judge_prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        return JudgmentResult(
            correct=result.get("correct", False),
            score=float(result.get("score", 0.0)),
            reasoning=result.get("reasoning", "No reasoning provided"),
            partial_credit=result.get("partial_credit", False)
        )

    except Exception as e:
        return JudgmentResult(
            correct=False,
            score=0.0,
            reasoning=f"Judgment failed: {str(e)}",
            partial_credit=False
        )


def judge_batch(
    evaluations: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.0
) -> List[JudgmentResult]:
    """
    Judge multiple answers in batch.

    Args:
        evaluations: List of dicts with keys: question, expected, actual
        model: OpenAI model for judging
        temperature: Temperature for judge model

    Returns:
        List of JudgmentResults in same order as input
    """
    results = []

    for eval_item in evaluations:
        result = judge_answer(
            question=eval_item["question"],
            expected_answer=eval_item["expected"],
            actual_answer=eval_item["actual"],
            model=model,
            temperature=temperature
        )
        results.append(result)

    return results


def judgment_to_dict(judgment: JudgmentResult) -> Dict[str, Any]:
    """Convert JudgmentResult to dictionary for JSON serialization."""
    return {
        "correct": judgment.correct,
        "score": judgment.score,
        "partial_credit": judgment.partial_credit,
        "reasoning": judgment.reasoning
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Judge answer accuracy")
    parser.add_argument("--question", "-q", required=True, help="The question")
    parser.add_argument("--expected", "-e", required=True, help="Expected answer")
    parser.add_argument("--actual", "-a", required=True, help="Actual answer to judge")
    parser.add_argument("--model", "-m", default="gpt-4o-mini", help="Judge model")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = judge_answer(
        question=args.question,
        expected_answer=args.expected,
        actual_answer=args.actual,
        model=args.model
    )

    if args.json:
        print(json.dumps(judgment_to_dict(result), indent=2))
    else:
        print(f"Correct: {result.correct}")
        print(f"Score: {result.score:.2f}")
        print(f"Partial credit: {result.partial_credit}")
        print(f"Reasoning: {result.reasoning}")
