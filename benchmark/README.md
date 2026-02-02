# IATF Benchmark Framework

Benchmark IATF's effectiveness in real agentic scenarios using OpenCode as the agent harness. Compares how agents find information with and without IATF indexing.

## Overview

This framework tests three approaches to document navigation:

| Approach | How It Works |
|----------|--------------|
| **Baseline** | Standard grep/read file navigation |
| **IATF** | Index-guided section navigation |
| **RAG (MCP)** | Vector similarity search via MCP server |

## Requirements

- Python 3.10+
- [OpenCode](https://github.com/opencode-ai/opencode) CLI
- OpenAI API key (for embeddings and LLM judging)
- Qdrant Cloud account (for RAG approach)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r mcp-rag-server/requirements.txt
```

### 2. Set Environment Variables

```bash
export OPENAI_API_KEY="your-openai-key"
export QDRANT_URL="https://your-cluster.qdrant.io"
export QDRANT_API_KEY="your-qdrant-key"
```

### 3. Configure RAG MCP Server (Optional)

Add to `~/.opencode/mcp.json`:

```json
{
  "servers": {
    "rag": {
      "command": "python",
      "args": ["/path/to/benchmark/mcp-rag-server/server.py"],
      "env": {
        "QDRANT_URL": "https://your-cluster.qdrant.io",
        "QDRANT_API_KEY": "your-api-key",
        "OPENAI_API_KEY": "your-openai-key"
      }
    }
  }
}
```

### 4. Ingest Documents (for RAG)

```bash
cd mcp-rag-server
python ingest.py ../datasets/bandar_frd/document.txt
```

### 5. Run Benchmark

```bash
cd scripts
python run_benchmark.py --dataset bandar_frd
```

## Project Structure

```
benchmark/
├── config.yaml                 # Benchmark configuration
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── datasets/
│   └── bandar_frd/
│       ├── document.iatf       # IATF format document
│       ├── document.txt        # Plain text version
│       └── questions.yaml      # 30 test questions
├── mcp-rag-server/             # RAG MCP server
│   ├── server.py               # MCP server implementation
│   ├── qdrant_client.py        # Qdrant Cloud wrapper
│   ├── embeddings.py           # OpenAI embeddings
│   ├── ingest.py               # Document ingestion
│   └── requirements.txt        # Server dependencies
├── scripts/
│   ├── run_benchmark.py        # Main orchestrator
│   ├── extract_metrics.py      # OpenCode SQLite query
│   ├── judge_accuracy.py       # LLM-based evaluation
│   └── generate_report.py      # IATF report generator
├── prompts/
│   ├── baseline.md             # Baseline system prompt
│   ├── iatf.md                 # IATF navigation prompt
│   └── rag_mcp.md              # RAG MCP prompt
└── results/                    # Output directory
```

## CLI Usage

### Full Benchmark

```bash
python scripts/run_benchmark.py --dataset bandar_frd
```

### Single Approach

```bash
python scripts/run_benchmark.py --dataset bandar_frd --approach iatf
python scripts/run_benchmark.py --dataset bandar_frd --approach baseline
python scripts/run_benchmark.py --dataset bandar_frd --approach rag_mcp
```

### Specific Question Types

```bash
python scripts/run_benchmark.py --dataset bandar_frd --type needle
python scripts/run_benchmark.py --dataset bandar_frd --type multihop
python scripts/run_benchmark.py --dataset bandar_frd --type aggregation
```

### Dry Run

```bash
python scripts/run_benchmark.py --dataset bandar_frd --dry-run
```

### Generate IATF Report

```bash
python scripts/generate_report.py --input results/benchmark_*.json
```

## Metrics Tracked

| Metric | Source | Description |
|--------|--------|-------------|
| `prompt_tokens` | OpenCode DB | Input tokens consumed |
| `completion_tokens` | OpenCode DB | Output tokens generated |
| `cost` | OpenCode DB | USD cost |
| `tool_calls` | OpenCode DB | Number of tool invocations |
| `latency_ms` | Timer | Time to completion |
| `accuracy` | LLM Judge | Correct answer (0/1) |
| `score` | LLM Judge | Quality score (0.0-1.0) |

## Question Types

### Needle-in-Haystack (10 questions)
Single fact retrieval from specific document locations.
Example: "What are the two types of admin users?"

### Multi-Hop (10 questions)
Require information from multiple sections.
Example: "How do Bandar Credits work across customer management and credits management?"

### Aggregation (10 questions)
Gather and synthesize information across the document.
Example: "List all admin portal modules mentioned."

## Configuration

Edit `config.yaml` to customize:

```yaml
opencode:
  path: "opencode"
  db_path: "~/.opencode/opencode.db"

model:
  provider: "openai"
  name: "gpt-4o-mini"

approaches:
  baseline:
    enabled: true
  iatf:
    enabled: true
  rag_mcp:
    enabled: true

evaluation:
  judge_model: "gpt-4o-mini"
```

## Results Format

Results are saved in both JSON (for analysis) and IATF (for dogfooding) formats.

### JSON Output

```json
{
  "metadata": {
    "timestamp": "2026-02-02T...",
    "model": "openai/gpt-4o-mini"
  },
  "summary": {
    "approaches": {
      "baseline": {"accuracy": 0.8, "avg_tokens": 1500, ...},
      "iatf": {"accuracy": 0.9, "avg_tokens": 800, ...}
    }
  },
  "results": [...]
}
```

### IATF Output

Results are also output in IATF format in `results/report_*.iatf`, demonstrating the format's utility for structured reports.

## Adding New Datasets

1. Create a new directory under `datasets/`
2. Add `document.iatf` (IATF format)
3. Add `document.txt` (plain text)
4. Add `questions.yaml` with test questions
5. Run ingestion for RAG: `python ingest.py datasets/new_dataset/document.txt`

## Troubleshooting

**OpenCode not found**
- Ensure `opencode` is in PATH or set full path in `config.yaml`

**Database errors**
- Check `~/.opencode/opencode.db` exists and has recent sessions

**RAG search returns no results**
- Verify documents were ingested: `python qdrant_client.py`
- Check Qdrant Cloud cluster is running

**Judge errors**
- Ensure `OPENAI_API_KEY` is set and valid
