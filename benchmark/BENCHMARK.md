# IATF FinanceBench Benchmark

This benchmark validates IATF format effectiveness by comparing against PageIndex's 98.7% accuracy on the FinanceBench dataset.

## Overview

The benchmark tests whether IATF's line-level granularity and self-indexing approach can match or exceed existing solutions while maintaining claimed token efficiency (80-95% savings).

## Quick Start

### 1. Install Dependencies

```bash
cd benchmark
pip install -r requirements.txt
```

### 2. Convert PDFs to IATF

```bash
# Convert all FinanceBench PDFs (requires OpenAI API key for best results)
export OPENAI_API_KEY="your-key-here"

python scripts/pdf_to_iatf.py \
  --input data/financebench/pdfs/ \
  --output iatf_docs/ \
  --validate \
  --verbose

# Or convert a subset for testing
python scripts/pdf_to_iatf.py \
  --input data/financebench/pdfs/ \
  --output iatf_docs/ \
  --limit 10 \
  --verbose
```

### 3. Run Evaluation

```bash
# Full evaluation
python scripts/evaluate.py \
  --data-dir data/financebench \
  --iatf-dir iatf_docs \
  --output results \
  --baseline \
  --verbose

# Quick test with 10 questions
python scripts/evaluate.py \
  --data-dir data/financebench \
  --iatf-dir iatf_docs \
  --output results \
  --limit 10 \
  --verbose
```

### 4. Analyze Results

```bash
python scripts/analyze.py --results results/
```

## Directory Structure

```
benchmark/
├── data/
│   ├── financebench/          # Cloned from patronus-ai/financebench
│   │   ├── data/
│   │   │   └── financebench_open_source.jsonl  # 150 questions
│   │   └── pdfs/              # Source PDF documents
│   └── Mafin2.5-FinanceBench/ # Evaluation code reference
│       └── eval.py
├── iatf_docs/                 # Converted IATF files
├── results/                   # Evaluation output
│   ├── iatf_results.jsonl
│   ├── baseline_results.jsonl
│   ├── summary.json
│   ├── benchmark_report.md
│   └── *.png                  # Visualizations
├── scripts/
│   ├── pdf_to_iatf.py        # PDF conversion
│   ├── iatf_retriever.py     # IATF retrieval system
│   ├── evaluate.py           # Evaluation pipeline
│   └── analyze.py            # Analysis and visualization
└── requirements.txt
```

## Scripts

### pdf_to_iatf.py

Converts financial PDF documents to IATF format.

**Features:**
- Text extraction with page info (pdfplumber/PyMuPDF)
- LLM-based section detection and summarization
- Heuristic fallback when LLM unavailable
- Automatic validation with `iatf validate`

**Usage:**
```bash
python scripts/pdf_to_iatf.py \
  --input <pdf_file_or_directory> \
  --output <iatf_file_or_directory> \
  [--validate] \
  [--api-key <openai_key>] \
  [--model gpt-4o] \
  [--limit N] \
  [--verbose]
```

### iatf_retriever.py

IATF-based retrieval system for document Q&A.

**Process:**
1. Load INDEX section only (minimal tokens)
2. Use LLM reasoning to select relevant sections
3. Load only selected sections by line number
4. Generate answer from focused context

**Usage as module:**
```python
from iatf_retriever import IATFRetriever

retriever = IATFRetriever("document.iatf", openai_api_key="...")
answer, metrics = retriever.answer_question("What was revenue in Q3?")

print(f"Answer: {answer}")
print(f"Tokens used: {metrics.total_tokens}")
print(f"Sections retrieved: {metrics.sections_retrieved}")
```

### evaluate.py

Runs full evaluation on FinanceBench dataset.

**Features:**
- Parallel question evaluation
- Answer equivalence checking (GPT-4o judge)
- Full document baseline comparison
- Detailed metrics tracking

**Usage:**
```bash
python scripts/evaluate.py \
  --data-dir data/financebench \
  --iatf-dir iatf_docs \
  --output results \
  [--baseline] \
  [--limit N] \
  [--concurrency 5] \
  [--model gpt-4o] \
  [--judge-model gpt-4o]
```

### analyze.py

Generates analysis and visualizations from results.

**Output:**
- `benchmark_report.md` - Comprehensive report
- `error_analysis.md` - Detailed error breakdown
- `accuracy_comparison.png` - Bar chart comparing methods
- `token_breakdown.png` - IATF token usage by component
- `token_comparison.png` - IATF vs baseline tokens
- `retrieval_analysis.png` - Accuracy vs retrieval ratio

## Metrics

### IATF Retrieval Metrics

| Metric | Description |
|--------|-------------|
| `index_tokens` | Tokens in INDEX section |
| `reasoning_tokens` | Tokens for section selection |
| `content_tokens` | Tokens in retrieved sections |
| `answer_tokens` | Tokens for answer generation |
| `total_tokens` | Sum of all tokens |
| `sections_retrieved` | Number of sections loaded |
| `retrieval_ratio` | sections_retrieved / total_sections |

### Evaluation Metrics

| Metric | Description |
|--------|-------------|
| `accuracy` | Percentage of correct answers |
| `latency` | Time per question (seconds) |
| `token_reduction` | (baseline - iatf) / baseline |

## Comparison: IATF vs PageIndex

| Aspect | PageIndex | IATF |
|--------|-----------|------|
| **Format** | JSON | Plain text |
| **Addressing** | Page numbers | Line numbers |
| **File Model** | PDF + JSON | Single file |
| **IDs** | Numeric | Semantic |
| **Editability** | Read-only | Fully editable |
| **Human Readable** | Requires viewer | Direct text |

## Success Criteria

**Must Have:**
- [ ] Accuracy ≥ 90% on FinanceBench
- [ ] Token reduction ≥ 50% vs full documents
- [ ] Complete evaluation on all 150 questions

**Nice to Have:**
- [ ] Accuracy ≥ 95% (close to PageIndex 98.7%)
- [ ] Token reduction ≥ 70%
- [ ] Latency ≤ 10s per question

## Troubleshooting

### Missing OpenAI API Key
```bash
export OPENAI_API_KEY="sk-..."
```

### PDF Extraction Errors
Install both libraries for better compatibility:
```bash
pip install pdfplumber pymupdf
```

### Rate Limiting
Reduce concurrency:
```bash
python scripts/evaluate.py --concurrency 2
```

### Missing IATF Files
Ensure conversion completed:
```bash
ls iatf_docs/*.iatf | wc -l
```

## References

- [FinanceBench Dataset](https://github.com/patronus-ai/financebench)
- [Mafin2.5-FinanceBench Eval](https://github.com/VectifyAI/Mafin2.5-FinanceBench)
- [PageIndex](https://github.com/VectifyAI/PageIndex)
- [IATF Specification](../SPECIFICATION.md)
