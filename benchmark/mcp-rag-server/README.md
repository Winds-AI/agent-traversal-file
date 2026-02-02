# MCP RAG Server for IATF Benchmark

This MCP server provides vector search capabilities for the IATF benchmark framework. It connects to Qdrant Cloud and exposes a `rag_search` tool that agents can use to retrieve relevant document chunks.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export QDRANT_URL="https://your-cluster.qdrant.io"
export QDRANT_API_KEY="your-api-key"
export OPENAI_API_KEY="your-openai-key"  # For generating embeddings
```

**Qdrant Cloud Setup:**
1. Create a free account at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a cluster
3. Copy the URL and generate an API key

### 3. Ingest Documents

Before running benchmarks, ingest the test documents:

```bash
# Ingest the plain text document
python ingest.py ../datasets/bandar_frd/document.txt --collection bandar_frd

# Or ingest from IATF (preserves section structure)
python ingest.py ../datasets/bandar_frd/document.iatf --collection bandar_frd
```

To recreate the collection (delete existing data):
```bash
python ingest.py document.txt --collection bandar_frd --recreate
```

### 4. Configure OpenCode

Add the MCP server to your OpenCode configuration at `~/.opencode/mcp.json`:

```json
{
  "servers": {
    "rag": {
      "command": "python",
      "args": ["/path/to/benchmark/mcp-rag-server/server.py"],
      "env": {
        "QDRANT_URL": "https://your-cluster.qdrant.io",
        "QDRANT_API_KEY": "your-api-key",
        "OPENAI_API_KEY": "your-openai-key",
        "RAG_COLLECTION": "bandar_frd"
      }
    }
  }
}
```

## Available Tools

### `rag_search`

Search the document for relevant content using semantic similarity.

**Parameters:**
- `query` (string, required): The search query
- `top_k` (integer, optional): Number of results to return (default: 5, max: 10)

**Example:**
```json
{
  "name": "rag_search",
  "arguments": {
    "query": "payment options for booking",
    "top_k": 5
  }
}
```

### `rag_info`

Get information about the document collection.

**Parameters:** None

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    OpenCode     │────▶│   MCP Server    │────▶│  Qdrant Cloud   │
│     Agent       │◀────│   (this repo)   │◀────│  Vector DB      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  OpenAI API     │
                        │  (embeddings)   │
                        └─────────────────┘
```

## Files

| File | Description |
|------|-------------|
| `server.py` | MCP server with `rag_search` tool |
| `qdrant_client.py` | Qdrant Cloud connection wrapper |
| `embeddings.py` | OpenAI embedding utilities |
| `ingest.py` | Document chunking and upload script |
| `requirements.txt` | Python dependencies |

## Testing

Test the server manually:

```bash
# Test embeddings
python embeddings.py

# Test Qdrant connection
python qdrant_client.py

# Test full search
python -c "
from embeddings import embed_text
from qdrant_client import get_qdrant_client, search

client = get_qdrant_client()
query = 'payment options'
embedding = embed_text(query)
results = search(client, 'bandar_frd', embedding, top_k=3)
for r in results:
    print(f'Score: {r.score:.3f}')
    print(f'Text: {r.text[:200]}...')
    print('---')
"
```

## Troubleshooting

**"QDRANT_URL not set"**
- Ensure environment variables are exported or set in MCP config

**"No relevant content found"**
- Check that documents have been ingested: `python qdrant_client.py`
- Verify collection name matches

**Connection timeout**
- Check Qdrant Cloud cluster is running
- Verify URL includes `https://`

**Empty embeddings**
- Ensure OPENAI_API_KEY is valid
- Check OpenAI API status
