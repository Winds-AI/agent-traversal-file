#!/usr/bin/env python3
"""
IATF FinanceBench Analysis and Visualization

Analyzes evaluation results and generates visualizations.

Usage:
    python analyze.py --results results/ --output results/
"""

import argparse
import json
from pathlib import Path
from typing import Optional

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    import seaborn as sns
except ImportError:
    sns = None


def load_results(
    results_dir: Path,
) -> tuple[Optional[list], Optional[list], Optional[dict]]:
    """Load evaluation results from files."""
    iatf_results = None
    baseline_results = None
    summary = None

    # Load IATF results
    iatf_path = results_dir / "iatf_results.jsonl"
    if iatf_path.exists():
        iatf_results = []
        with open(iatf_path, "r") as f:
            for line in f:
                if line.strip():
                    iatf_results.append(json.loads(line))

    # Load baseline results
    baseline_path = results_dir / "baseline_results.jsonl"
    if baseline_path.exists():
        baseline_results = []
        with open(baseline_path, "r") as f:
            for line in f:
                if line.strip():
                    baseline_results.append(json.loads(line))

    # Load summary
    summary_path = results_dir / "summary.json"
    if summary_path.exists():
        with open(summary_path, "r") as f:
            summary = json.load(f)

    return iatf_results, baseline_results, summary


def analyze_errors(results: list[dict]) -> dict:
    """Analyze error patterns in results."""
    errors = {
        "retrieval": [],  # Correct section not loaded
        "reasoning": [],  # Section loaded but wrong answer
        "conversion": [],  # PDF->IATF conversion issue
        "api": [],  # API errors
        "missing": [],  # Missing files
    }

    for r in results:
        if r.get("error"):
            error_msg = r["error"].lower()
            if "not found" in error_msg:
                errors["missing"].append(r)
            elif "api" in error_msg or "openai" in error_msg or "rate" in error_msg:
                errors["api"].append(r)
            else:
                errors["conversion"].append(r)
        elif not r.get("correct", False) and r.get("predicted_answer"):
            # Wrong answer - try to classify
            if r.get("sections_retrieved", 0) == 0:
                errors["retrieval"].append(r)
            else:
                errors["reasoning"].append(r)

    return errors


def generate_error_report(errors: dict, output_path: Path):
    """Generate detailed error analysis report."""
    lines = [
        "# IATF FinanceBench Error Analysis",
        "",
        "## Error Summary",
        "",
        f"- **Retrieval errors** (wrong sections loaded): {len(errors['retrieval'])}",
        f"- **Reasoning errors** (right sections, wrong answer): {len(errors['reasoning'])}",
        f"- **Conversion errors** (PDF->IATF issues): {len(errors['conversion'])}",
        f"- **API errors**: {len(errors['api'])}",
        f"- **Missing files**: {len(errors['missing'])}",
        "",
    ]

    # Detail for each error type
    for error_type, error_list in errors.items():
        if not error_list:
            continue

        lines.append(f"## {error_type.title()} Errors ({len(error_list)})")
        lines.append("")

        for i, err in enumerate(error_list[:10], 1):  # Limit to first 10
            lines.append(f"### {i}. {err.get('question_id', 'Unknown')}")
            lines.append(f"**Document:** {err.get('doc_name', 'Unknown')}")
            lines.append(f"**Question:** {err.get('question', 'N/A')}")
            lines.append(f"**Gold Answer:** {err.get('gold_answer', 'N/A')}")
            lines.append(f"**Predicted:** {err.get('predicted_answer', 'N/A')}")
            if err.get("error"):
                lines.append(f"**Error:** {err.get('error')}")
            lines.append("")

        if len(error_list) > 10:
            lines.append(f"*... and {len(error_list) - 10} more*")
            lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def generate_visualizations(
    iatf_results: list[dict], baseline_results: Optional[list[dict]], output_dir: Path
):
    """Generate visualization charts."""
    if plt is None or pd is None:
        print("Warning: matplotlib/pandas not available, skipping visualizations")
        return

    # Convert to DataFrames
    df_iatf = pd.DataFrame(iatf_results)
    df_baseline = pd.DataFrame(baseline_results) if baseline_results else None

    # Filter valid results
    df_iatf_valid = df_iatf[df_iatf["error"].isna()].copy()

    # Set style
    if sns:
        sns.set_style("whitegrid")

    # 1. Accuracy Comparison Bar Chart
    fig, ax = plt.subplots(figsize=(10, 6))

    accuracies = {"IATF": df_iatf_valid["correct"].mean() * 100}
    if df_baseline is not None:
        df_baseline_valid = df_baseline[df_baseline["error"].isna()].copy()
        accuracies["Full Document"] = df_baseline_valid["correct"].mean() * 100

    # Add PageIndex reference
    accuracies["PageIndex (Reference)"] = 98.7

    colors = ["#2ecc71", "#3498db", "#9b59b6"][: len(accuracies)]
    bars = ax.bar(accuracies.keys(), accuracies.values(), color=colors)

    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Accuracy Comparison on FinanceBench")
    ax.set_ylim(0, 105)

    # Add value labels
    for bar, val in zip(bars, accuracies.values()):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{val:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.tight_layout()
    plt.savefig(output_dir / "accuracy_comparison.png", dpi=150)
    plt.close()

    # 2. Token Usage Breakdown
    if "index_tokens" in df_iatf_valid.columns:
        fig, ax = plt.subplots(figsize=(12, 6))

        token_cols = [
            "index_tokens",
            "reasoning_tokens",
            "content_tokens",
            "answer_tokens",
        ]
        token_data = df_iatf_valid[token_cols].mean()

        colors = ["#e74c3c", "#f39c12", "#2ecc71", "#3498db"]
        ax.bar(range(len(token_cols)), token_data.values, color=colors)
        ax.set_xticks(range(len(token_cols)))
        ax.set_xticklabels(["Index", "Reasoning", "Content", "Answer"])
        ax.set_ylabel("Average Tokens")
        ax.set_title("Token Usage Breakdown (IATF Retrieval)")

        # Add total
        total = token_data.sum()
        ax.axhline(
            y=total / 4,
            color="gray",
            linestyle="--",
            label=f"Avg per component: {total / 4:.0f}",
        )
        ax.legend()

        plt.tight_layout()
        plt.savefig(output_dir / "token_breakdown.png", dpi=150)
        plt.close()

    # 3. Token Comparison (IATF vs Baseline)
    if df_baseline is not None and "total_tokens" in df_baseline.columns:
        fig, ax = plt.subplots(figsize=(10, 6))

        df_baseline_valid = df_baseline[df_baseline["error"].isna()]

        avg_tokens = {
            "IATF": df_iatf_valid["total_tokens"].mean(),
            "Full Document": df_baseline_valid["total_tokens"].mean(),
        }

        colors = ["#2ecc71", "#e74c3c"]
        bars = ax.bar(avg_tokens.keys(), avg_tokens.values(), color=colors)

        ax.set_ylabel("Average Tokens per Question")
        ax.set_title("Token Usage Comparison")

        for bar, val in zip(bars, avg_tokens.values()):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 100,
                f"{val:.0f}",
                ha="center",
                va="bottom",
                fontsize=10,
            )

        # Add reduction percentage
        if avg_tokens["Full Document"] > 0:
            reduction = (
                (avg_tokens["Full Document"] - avg_tokens["IATF"])
                / avg_tokens["Full Document"]
                * 100
            )
            ax.text(
                0.5,
                0.95,
                f"Token Reduction: {reduction:.1f}%",
                transform=ax.transAxes,
                ha="center",
                fontsize=12,
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
            )

        plt.tight_layout()
        plt.savefig(output_dir / "token_comparison.png", dpi=150)
        plt.close()

    # 4. Retrieval Ratio Distribution
    if "retrieval_ratio" in df_iatf_valid.columns:
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.hist(
            df_iatf_valid["retrieval_ratio"] * 100,
            bins=20,
            color="#3498db",
            edgecolor="white",
        )
        ax.set_xlabel("Retrieval Ratio (%)")
        ax.set_ylabel("Number of Questions")
        ax.set_title("Distribution of Sections Retrieved")
        ax.axvline(
            df_iatf_valid["retrieval_ratio"].mean() * 100,
            color="red",
            linestyle="--",
            label=f"Mean: {df_iatf_valid['retrieval_ratio'].mean() * 100:.1f}%",
        )
        ax.legend()

        plt.tight_layout()
        plt.savefig(output_dir / "retrieval_distribution.png", dpi=150)
        plt.close()

    # 5. Latency Distribution
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(
        df_iatf_valid["latency_seconds"], bins=20, color="#9b59b6", edgecolor="white"
    )
    ax.set_xlabel("Latency (seconds)")
    ax.set_ylabel("Number of Questions")
    ax.set_title("Response Latency Distribution")
    ax.axvline(
        df_iatf_valid["latency_seconds"].mean(),
        color="red",
        linestyle="--",
        label=f"Mean: {df_iatf_valid['latency_seconds'].mean():.2f}s",
    )
    ax.legend()

    plt.tight_layout()
    plt.savefig(output_dir / "latency_distribution.png", dpi=150)
    plt.close()

    # 6. Accuracy vs Retrieval Ratio Scatter
    if "retrieval_ratio" in df_iatf_valid.columns:
        fig, ax = plt.subplots(figsize=(10, 6))

        correct = df_iatf_valid[df_iatf_valid["correct"] == True]
        incorrect = df_iatf_valid[df_iatf_valid["correct"] == False]

        ax.scatter(
            correct["retrieval_ratio"] * 100,
            correct["total_tokens"],
            c="green",
            alpha=0.6,
            label="Correct",
            s=50,
        )
        ax.scatter(
            incorrect["retrieval_ratio"] * 100,
            incorrect["total_tokens"],
            c="red",
            alpha=0.6,
            label="Incorrect",
            s=50,
        )

        ax.set_xlabel("Retrieval Ratio (%)")
        ax.set_ylabel("Total Tokens")
        ax.set_title("Correctness vs Retrieval Efficiency")
        ax.legend()

        plt.tight_layout()
        plt.savefig(output_dir / "retrieval_analysis.png", dpi=150)
        plt.close()

    print(f"Generated visualizations in {output_dir}")


def generate_markdown_report(
    iatf_results: list[dict],
    baseline_results: Optional[list[dict]],
    summary: Optional[dict],
    output_path: Path,
):
    """Generate comprehensive markdown report."""
    lines = [
        "# IATF FinanceBench Benchmark Report",
        "",
        "## Executive Summary",
        "",
    ]

    # Calculate metrics
    df_iatf = None
    if pd:
        df_iatf = pd.DataFrame(iatf_results)
        df_iatf_valid = df_iatf[df_iatf["error"].isna()]

        accuracy = df_iatf_valid["correct"].mean() * 100
        avg_tokens = df_iatf_valid["total_tokens"].mean()
        avg_latency = df_iatf_valid["latency_seconds"].mean()

        lines.append(f"- **Accuracy:** {accuracy:.1f}% (vs PageIndex 98.7%)")

        if baseline_results and pd:
            df_baseline = pd.DataFrame(baseline_results)
            df_baseline_valid = df_baseline[df_baseline["error"].isna()]
            baseline_tokens = df_baseline_valid["total_tokens"].mean()
            reduction = (
                (baseline_tokens - avg_tokens) / baseline_tokens * 100
                if baseline_tokens > 0
                else 0
            )
            lines.append(
                f"- **Token Savings:** {reduction:.1f}% vs full document baseline"
            )

        lines.append(f"- **Avg Latency:** {avg_latency:.2f}s per question")
        lines.append(f"- **Total Questions Evaluated:** {len(df_iatf_valid)}")

    lines.extend(
        [
            "",
            "## Methodology",
            "",
            "### PDF to IATF Conversion",
            "- Financial documents (10-K, 10-Q, 8-K, earnings calls) converted to IATF format",
            "- Section detection using LLM-based analysis with heuristic fallback",
            "- Automatic summary generation for each section",
            "",
            "### IATF Retrieval Process",
            "1. Load INDEX section only (minimal tokens)",
            "2. Use LLM reasoning to select relevant sections based on question",
            "3. Load only selected sections by line number",
            "4. Generate answer from focused context",
            "",
            "### Evaluation",
            "- Answer equivalence checked using GPT-4o as judge",
            "- Follows FinanceBench evaluation protocol with numerical flexibility",
            "",
            "## Results",
            "",
        ]
    )

    if df_iatf is not None:
        df_valid = df_iatf[df_iatf["error"].isna()]

        lines.extend(
            [
                "### IATF Retrieval Performance",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Accuracy | {df_valid['correct'].mean() * 100:.1f}% |",
                f"| Avg Total Tokens | {df_valid['total_tokens'].mean():.0f} |",
                f"| Avg Index Tokens | {df_valid.get('index_tokens', pd.Series([0])).mean():.0f} |",
                f"| Avg Content Tokens | {df_valid.get('content_tokens', pd.Series([0])).mean():.0f} |",
                f"| Avg Sections Retrieved | {df_valid.get('sections_retrieved', pd.Series([0])).mean():.1f} |",
                f"| Avg Retrieval Ratio | {df_valid.get('retrieval_ratio', pd.Series([0])).mean() * 100:.1f}% |",
                f"| Avg Latency | {df_valid['latency_seconds'].mean():.2f}s |",
                "",
            ]
        )

        if baseline_results and pd:
            df_baseline = pd.DataFrame(baseline_results)
            df_baseline_valid = df_baseline[df_baseline["error"].isna()]

            lines.extend(
                [
                    "### Comparison with Full Document Baseline",
                    "",
                    "| Metric | IATF | Full Document | Delta |",
                    "|--------|------|---------------|-------|",
                    f"| Accuracy | {df_valid['correct'].mean() * 100:.1f}% | {df_baseline_valid['correct'].mean() * 100:.1f}% | {(df_valid['correct'].mean() - df_baseline_valid['correct'].mean()) * 100:+.1f}% |",
                    f"| Avg Tokens | {df_valid['total_tokens'].mean():.0f} | {df_baseline_valid['total_tokens'].mean():.0f} | {df_valid['total_tokens'].mean() - df_baseline_valid['total_tokens'].mean():+.0f} |",
                    f"| Avg Latency | {df_valid['latency_seconds'].mean():.2f}s | {df_baseline_valid['latency_seconds'].mean():.2f}s | {df_valid['latency_seconds'].mean() - df_baseline_valid['latency_seconds'].mean():+.2f}s |",
                    "",
                ]
            )

    lines.extend(
        [
            "## Visualizations",
            "",
            "![Accuracy Comparison](accuracy_comparison.png)",
            "",
            "![Token Breakdown](token_breakdown.png)",
            "",
            "![Token Comparison](token_comparison.png)",
            "",
            "![Retrieval Analysis](retrieval_analysis.png)",
            "",
            "## Key Differences: IATF vs PageIndex",
            "",
            "| Aspect | PageIndex | IATF |",
            "|--------|-----------|------|",
            "| **Format** | JSON | Plain text with delimiters |",
            "| **Addressing** | Page numbers (coarse) | Line numbers (fine) |",
            "| **File Model** | Two files (PDF + JSON index) | Single file (INDEX + CONTENT) |",
            "| **Hierarchy** | JSON nesting (unlimited depth) | Markdown levels (depth: 2) |",
            '| **IDs** | Numeric (`"0006"`) | Semantic (`#financial-stability`) |',
            "| **Editability** | Read-only PDFs | Fully editable text |",
            "| **Human Readable** | Requires JSON viewer | Direct text scanning |",
            "",
            "## Conclusions",
            "",
            "Based on this benchmark evaluation:",
            "",
            "1. **Token Efficiency:** IATF format achieves significant token reduction by loading only relevant sections",
            "2. **Accuracy:** [To be completed based on actual results]",
            "3. **Latency:** Comparable to full document approach due to LLM reasoning overhead",
            "4. **Strengths:** Line-level precision, human readability, single-file format",
            "5. **Weaknesses:** Requires document conversion, section detection quality varies",
            "",
            "## Future Improvements",
            "",
            "- [ ] Improve section detection for complex financial tables",
            "- [ ] Add financial-specific metadata (metrics, periods, entities)",
            "- [ ] Implement multi-hop retrieval following cross-references",
            "- [ ] Cache parsed indices for repeated queries",
            "",
        ]
    )

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Analyze IATF benchmark results")
    parser.add_argument(
        "--results",
        "-r",
        default="../results",
        help="Results directory containing evaluation output",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output directory for analysis (default: same as results)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent
    results_dir = Path(args.results)
    if not results_dir.is_absolute():
        results_dir = script_dir / results_dir

    output_dir = Path(args.output) if args.output else results_dir
    if not output_dir.is_absolute():
        output_dir = script_dir / output_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load results
    print(f"Loading results from {results_dir}...")
    iatf_results, baseline_results, summary = load_results(results_dir)

    if not iatf_results:
        print("Error: No IATF results found")
        return

    print(f"Loaded {len(iatf_results)} IATF results")
    if baseline_results:
        print(f"Loaded {len(baseline_results)} baseline results")

    # Analyze errors
    print("\nAnalyzing errors...")
    errors = analyze_errors(iatf_results)
    generate_error_report(errors, output_dir / "error_analysis.md")

    # Generate visualizations
    print("Generating visualizations...")
    generate_visualizations(iatf_results, baseline_results, output_dir)

    # Generate report
    print("Generating report...")
    generate_markdown_report(
        iatf_results, baseline_results, summary, output_dir / "benchmark_report.md"
    )

    print(f"\nAnalysis complete. Output in {output_dir}")
    print("  - error_analysis.md")
    print("  - benchmark_report.md")
    print("  - *.png visualizations")


if __name__ == "__main__":
    main()
