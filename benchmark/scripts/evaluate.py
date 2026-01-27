#!/usr/bin/env python3
"""
IATF FinanceBench Evaluation Pipeline

Runs full evaluation on the FinanceBench dataset using IATF format.
Compares IATF retrieval against full document baseline.

Usage:
    python evaluate.py --iatf-dir iatf_docs/ --output results/
    python evaluate.py --limit 10 --verbose  # Test run with 10 questions
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from iatf_retriever import IATFRetriever, RetrievalMetrics, count_tokens

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from tqdm import tqdm
    from tqdm.asyncio import tqdm as atqdm
except ImportError:
    tqdm = None
    atqdm = None


async def check_answer_equivalence(
    predicted_answer: str,
    gold_answer: str,
    question: str,
    client,
    model: str = "gpt-4o",
) -> bool:
    """
    Check if predicted answer is equivalent to gold answer.
    Based on Mafin2.5-FinanceBench/eval.py evaluation logic.
    """
    prompt = f"""You are an expert evaluator for AI-generated responses to financial queries. 
Your task is to determine whether the AI-generated answer correctly answers the query based on the golden answer provided by a human expert.

Numerical Accuracy: 
- Rounding differences should be **ignored** if they do not meaningfully change the conclusion.
- You can allow some flexibility in accuracy. For example, 1.2 is considered similar to 1.23. Two numbers are considered similar if one can be rounded to the other.
- Fractions, percentage, and numerics could be considered similar, for example: "11 of 14" is considered equivalent to "79%" and "0.79".

Evaluation Criteria:
- If the golden answer or any of its equivalence can be inferred or generated from the AI-generated answer, then the AI-generated answer is considered correct.
- If any number, percentage, fraction, or figure in the golden answer is not present in the AI-generated answer, but can be inferred or generated from the AI-generated answer or implicitly exist in the AI-generated answer, then the AI-generated answer is considered correct.
- The AI-generated answer is considered correct if it conveys the same or similar meaning, conclusion, or rationale as the golden answer.
- If the AI-generated answer is a superset of the golden answer, it is also considered correct.
- If the AI-generated answer provides a valid answer or reasonable interpretation compared to the golden answer, it is considered correct.
- If the AI-generated answer contains subjective judgments or opinions, it is considered correct as long as they are reasonable and justifiable compared to the golden answer.
- Otherwise, the AI-generated answer is incorrect.

Inputs:
- Query: {question}
- AI-Generated Answer: {predicted_answer}
- Golden Answer: {gold_answer}

Your output should be ONLY a boolean value: `True` or `False`, nothing else."""

    for retry in range(3):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10,
            )

            response_text = response.choices[0].message.content.strip().lower()

            if "true" in response_text:
                return True
            elif "false" in response_text:
                return False
            else:
                # Ambiguous response, default to False
                return False

        except Exception as e:
            print(f"Evaluation error (retry {retry + 1}): {e}")
            await asyncio.sleep(1)

    return False


def load_financebench_questions(data_path: str) -> list[dict]:
    """Load FinanceBench questions from JSONL file."""
    questions = []
    jsonl_path = Path(data_path) / "financebench_open_source.jsonl"

    if not jsonl_path.exists():
        # Try alternate path
        jsonl_path = Path(data_path) / "data" / "financebench_open_source.jsonl"

    if not jsonl_path.exists():
        raise FileNotFoundError(f"Questions file not found: {jsonl_path}")

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    return questions


def find_iatf_file(doc_name: str, iatf_dir: Path) -> Optional[Path]:
    """Find the IATF file corresponding to a document name."""
    # Try exact match
    iatf_path = iatf_dir / f"{doc_name}.iatf"
    if iatf_path.exists():
        return iatf_path

    # Try lowercase
    iatf_path = iatf_dir / f"{doc_name.lower()}.iatf"
    if iatf_path.exists():
        return iatf_path

    # Try with underscores replaced
    alt_name = doc_name.replace("-", "_")
    iatf_path = iatf_dir / f"{alt_name}.iatf"
    if iatf_path.exists():
        return iatf_path

    return None


async def evaluate_single_question(
    question_data: dict,
    iatf_dir: Path,
    openai_api_key: str,
    model: str,
    judge_model: str,
    verbose: bool = False,
) -> dict:
    """Evaluate a single question using IATF retrieval."""
    question_id = question_data.get("financebench_id", "unknown")
    question_text = question_data["question"]
    gold_answer = question_data["answer"]
    doc_name = question_data["doc_name"]

    result = {
        "question_id": question_id,
        "doc_name": doc_name,
        "question": question_text,
        "gold_answer": gold_answer,
        "predicted_answer": None,
        "correct": False,
        "error": None,
        "latency_seconds": 0,
        "index_tokens": 0,
        "reasoning_tokens": 0,
        "content_tokens": 0,
        "answer_tokens": 0,
        "total_tokens": 0,
        "sections_retrieved": 0,
        "total_sections": 0,
        "retrieval_ratio": 0,
    }

    # Find IATF file
    iatf_path = find_iatf_file(doc_name, iatf_dir)

    if not iatf_path:
        result["error"] = f"IATF file not found for {doc_name}"
        return result

    try:
        # Initialize retriever
        retriever = IATFRetriever(
            str(iatf_path), openai_api_key=openai_api_key, model=model
        )

        # Answer question with timing
        start_time = time.time()
        predicted_answer, metrics = retriever.answer_question(question_text)
        latency = time.time() - start_time

        result["predicted_answer"] = predicted_answer
        result["latency_seconds"] = latency
        result["index_tokens"] = metrics.index_tokens
        result["reasoning_tokens"] = metrics.reasoning_tokens
        result["content_tokens"] = metrics.content_tokens
        result["answer_tokens"] = metrics.answer_tokens
        result["total_tokens"] = metrics.total_tokens
        result["sections_retrieved"] = metrics.sections_retrieved
        result["total_sections"] = metrics.total_sections
        result["retrieval_ratio"] = metrics.retrieval_ratio

        # Evaluate correctness
        if AsyncOpenAI:
            client = AsyncOpenAI(api_key=openai_api_key)
            result["correct"] = await check_answer_equivalence(
                predicted_answer, gold_answer, question_text, client, model=judge_model
            )
            await client.close()

    except Exception as e:
        result["error"] = str(e)
        if verbose:
            print(f"Error on {question_id}: {e}")

    return result


async def evaluate_baseline_single(
    question_data: dict,
    iatf_dir: Path,
    openai_api_key: str,
    model: str,
    judge_model: str,
) -> dict:
    """Evaluate using full document baseline (no IATF indexing)."""
    question_id = question_data.get("financebench_id", "unknown")
    question_text = question_data["question"]
    gold_answer = question_data["answer"]
    doc_name = question_data["doc_name"]

    result = {
        "question_id": question_id,
        "doc_name": doc_name,
        "question": question_text,
        "gold_answer": gold_answer,
        "predicted_answer": None,
        "correct": False,
        "error": None,
        "latency_seconds": 0,
        "total_tokens": 0,
    }

    iatf_path = find_iatf_file(doc_name, iatf_dir)

    if not iatf_path:
        result["error"] = f"IATF file not found for {doc_name}"
        return result

    try:
        retriever = IATFRetriever(
            str(iatf_path), openai_api_key=openai_api_key, model=model
        )

        start_time = time.time()
        predicted_answer, total_tokens = retriever.answer_with_full_context(
            question_text
        )
        latency = time.time() - start_time

        result["predicted_answer"] = predicted_answer
        result["latency_seconds"] = latency
        result["total_tokens"] = total_tokens

        if AsyncOpenAI:
            client = AsyncOpenAI(api_key=openai_api_key)
            result["correct"] = await check_answer_equivalence(
                predicted_answer, gold_answer, question_text, client, model=judge_model
            )
            await client.close()

    except Exception as e:
        result["error"] = str(e)

    return result


async def run_evaluation(
    questions: list[dict],
    iatf_dir: Path,
    openai_api_key: str,
    model: str = "gpt-4o",
    judge_model: str = "gpt-4o",
    include_baseline: bool = False,
    verbose: bool = False,
    concurrency: int = 5,
) -> tuple[list[dict], list[dict]]:
    """Run evaluation on all questions."""
    iatf_results = []
    baseline_results = []

    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(concurrency)

    async def eval_with_semaphore(q):
        async with semaphore:
            return await evaluate_single_question(
                q, iatf_dir, openai_api_key, model, judge_model, verbose
            )

    async def baseline_with_semaphore(q):
        async with semaphore:
            return await evaluate_baseline_single(
                q, iatf_dir, openai_api_key, model, judge_model
            )

    # IATF evaluation
    print(f"Evaluating {len(questions)} questions with IATF retrieval...")

    if atqdm:
        tasks = [eval_with_semaphore(q) for q in questions]
        iatf_results = await atqdm.gather(*tasks, desc="IATF Evaluation")
    else:
        for i, q in enumerate(questions):
            if verbose:
                print(
                    f"[{i + 1}/{len(questions)}] {q.get('financebench_id', 'unknown')}"
                )
            result = await eval_with_semaphore(q)
            iatf_results.append(result)

    # Baseline evaluation (optional)
    if include_baseline:
        print(f"\nEvaluating {len(questions)} questions with full document baseline...")

        if atqdm:
            tasks = [baseline_with_semaphore(q) for q in questions]
            baseline_results = await atqdm.gather(*tasks, desc="Baseline Evaluation")
        else:
            for i, q in enumerate(questions):
                if verbose:
                    print(
                        f"[{i + 1}/{len(questions)}] Baseline: {q.get('financebench_id', 'unknown')}"
                    )
                result = await baseline_with_semaphore(q)
                baseline_results.append(result)

    return iatf_results, baseline_results


def calculate_statistics(results: list[dict]) -> dict:
    """Calculate summary statistics from results."""
    valid_results = [r for r in results if r.get("error") is None]

    if not valid_results:
        return {"error": "No valid results"}

    correct_count = sum(1 for r in valid_results if r.get("correct", False))
    total_count = len(valid_results)

    stats = {
        "total_questions": len(results),
        "valid_questions": total_count,
        "errors": len(results) - total_count,
        "correct": correct_count,
        "accuracy": correct_count / total_count if total_count > 0 else 0,
        "avg_latency": sum(r.get("latency_seconds", 0) for r in valid_results)
        / total_count,
        "avg_total_tokens": sum(r.get("total_tokens", 0) for r in valid_results)
        / total_count,
    }

    # IATF-specific metrics
    if "sections_retrieved" in valid_results[0]:
        stats["avg_index_tokens"] = (
            sum(r.get("index_tokens", 0) for r in valid_results) / total_count
        )
        stats["avg_reasoning_tokens"] = (
            sum(r.get("reasoning_tokens", 0) for r in valid_results) / total_count
        )
        stats["avg_content_tokens"] = (
            sum(r.get("content_tokens", 0) for r in valid_results) / total_count
        )
        stats["avg_sections_retrieved"] = (
            sum(r.get("sections_retrieved", 0) for r in valid_results) / total_count
        )
        stats["avg_retrieval_ratio"] = (
            sum(r.get("retrieval_ratio", 0) for r in valid_results) / total_count
        )

    return stats


def save_results(
    iatf_results: list[dict],
    baseline_results: list[dict],
    output_dir: Path,
    iatf_stats: dict,
    baseline_stats: dict,
):
    """Save evaluation results to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save IATF results
    with open(output_dir / "iatf_results.jsonl", "w") as f:
        for r in iatf_results:
            f.write(json.dumps(r) + "\n")

    # Save baseline results
    if baseline_results:
        with open(output_dir / "baseline_results.jsonl", "w") as f:
            for r in baseline_results:
                f.write(json.dumps(r) + "\n")

    # Save summary
    summary = {
        "iatf": iatf_stats,
        "baseline": baseline_stats if baseline_results else None,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Save as CSV if pandas available
    if pd:
        df_iatf = pd.DataFrame(iatf_results)
        df_iatf.to_csv(output_dir / "iatf_results.csv", index=False)

        if baseline_results:
            df_baseline = pd.DataFrame(baseline_results)
            df_baseline.to_csv(output_dir / "baseline_results.csv", index=False)


def print_summary(iatf_stats: dict, baseline_stats: dict = None):
    """Print evaluation summary."""
    print("\n" + "=" * 60)
    print("IATF FinanceBench Evaluation Results")
    print("=" * 60)

    print(f"\nIATF Retrieval:")
    print(
        f"  Accuracy: {iatf_stats['accuracy'] * 100:.2f}% ({iatf_stats['correct']}/{iatf_stats['valid_questions']})"
    )
    print(f"  Avg Total Tokens: {iatf_stats['avg_total_tokens']:.0f}")
    print(f"  Avg Latency: {iatf_stats['avg_latency']:.2f}s")

    if "avg_retrieval_ratio" in iatf_stats:
        print(f"  Avg Sections Retrieved: {iatf_stats['avg_sections_retrieved']:.1f}")
        print(f"  Avg Retrieval Ratio: {iatf_stats['avg_retrieval_ratio'] * 100:.1f}%")

    if iatf_stats.get("errors", 0) > 0:
        print(f"  Errors: {iatf_stats['errors']}")

    if baseline_stats:
        print(f"\nFull Document Baseline:")
        print(
            f"  Accuracy: {baseline_stats['accuracy'] * 100:.2f}% ({baseline_stats['correct']}/{baseline_stats['valid_questions']})"
        )
        print(f"  Avg Total Tokens: {baseline_stats['avg_total_tokens']:.0f}")
        print(f"  Avg Latency: {baseline_stats['avg_latency']:.2f}s")

        # Token reduction
        if baseline_stats["avg_total_tokens"] > 0:
            reduction = (
                baseline_stats["avg_total_tokens"] - iatf_stats["avg_total_tokens"]
            ) / baseline_stats["avg_total_tokens"]
            print(f"\nToken Reduction: {reduction * 100:.1f}%")

        # Accuracy comparison
        acc_diff = iatf_stats["accuracy"] - baseline_stats["accuracy"]
        print(f"Accuracy Delta: {acc_diff * 100:+.2f}%")

    print("=" * 60 + "\n")


async def main_async():
    parser = argparse.ArgumentParser(description="Evaluate IATF on FinanceBench")
    parser.add_argument(
        "--data-dir",
        default="../data/financebench",
        help="Path to financebench data directory",
    )
    parser.add_argument(
        "--iatf-dir", default="../iatf_docs", help="Path to IATF files directory"
    )
    parser.add_argument(
        "--output", default="../results", help="Output directory for results"
    )
    parser.add_argument(
        "--api-key", default=os.environ.get("OPENAI_API_KEY"), help="OpenAI API key"
    )
    parser.add_argument(
        "--model", default="gpt-4o", help="Model for answering questions"
    )
    parser.add_argument(
        "--judge-model", default="gpt-4o", help="Model for evaluating answers"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit number of questions (0 = all)"
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Also run full document baseline comparison",
    )
    parser.add_argument(
        "--concurrency", type=int, default=5, help="Number of concurrent API calls"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent
    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = script_dir / data_dir

    iatf_dir = Path(args.iatf_dir)
    if not iatf_dir.is_absolute():
        iatf_dir = script_dir / iatf_dir

    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = script_dir / output_dir

    # Check API key
    if not args.api_key:
        print("Error: OpenAI API key required. Set OPENAI_API_KEY or use --api-key")
        sys.exit(1)

    # Load questions
    print(f"Loading questions from {data_dir}...")
    try:
        questions = load_financebench_questions(str(data_dir))
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if args.limit > 0:
        questions = questions[: args.limit]

    print(f"Loaded {len(questions)} questions")

    # Check IATF files exist
    missing_count = 0
    for q in questions:
        if not find_iatf_file(q["doc_name"], iatf_dir):
            missing_count += 1
            if args.verbose:
                print(f"  Missing: {q['doc_name']}")

    if missing_count > 0:
        print(f"Warning: {missing_count} IATF files missing")
        if missing_count == len(questions):
            print("Error: No IATF files found. Run pdf_to_iatf.py first.")
            sys.exit(1)

    # Run evaluation
    iatf_results, baseline_results = await run_evaluation(
        questions,
        iatf_dir,
        args.api_key,
        model=args.model,
        judge_model=args.judge_model,
        include_baseline=args.baseline,
        verbose=args.verbose,
        concurrency=args.concurrency,
    )

    # Calculate statistics
    iatf_stats = calculate_statistics(iatf_results)
    baseline_stats = calculate_statistics(baseline_results) if baseline_results else {}

    # Print summary
    print_summary(iatf_stats, baseline_stats if baseline_results else None)

    # Save results
    save_results(iatf_results, baseline_results, output_dir, iatf_stats, baseline_stats)
    print(f"Results saved to {output_dir}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
