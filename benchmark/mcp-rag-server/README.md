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
```

**Qdrant Cloud Setup:**
1. Create a free account at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a cluster
3. Copy the URL and generate an API key

### 3. Ingest Documents

Before running benchmarks, ingest the test documents:

```bash
# Ingest the text document
python ingest.py ../datasets/bandar_frd/document.txt --collection bandar_frd
```

To recreate the collection (delete existing data):
```bash
python ingest.py ../datasets/bandar_frd/document.txt --collection bandar_frd --recreate
```

### 4. Configure OpenCode

The benchmark harness isolates OpenCode config per run and enables MCP by writing a
temporary `opencode.json` based on `benchmark/opencode.json`. You do not need to edit
any user-global OpenCode configuration.

If you need to change how OpenCode connects to the MCP server (host/port), edit
`benchmark/opencode.json`.

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

## Chunking Strategy

Documents are chunked into 512-token segments with 50-token overlap using `cl100k_base` (via tiktoken). Embeddings are generated in batches of 10 chunks. The server uses `sentence-transformers/all-MiniLM-L6-v2` for local embeddings.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    OpenCode     │────▶│   MCP Server    │────▶│  Qdrant Cloud   │
│     Agent       │◀────│   (this repo)   │◀────│  Vector DB      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │ SentenceTransf. │
                        │ (local embed)   │
                        └─────────────────┘
```

## Files

| File | Description |
|------|-------------|
| `server.py` | MCP server with `rag_search` tool |
| `qdrant_store.py` | Qdrant Cloud connection wrapper |
| `embeddings.py` | sentence-transformers embedding utilities |
| `ingest.py` | Document chunking and upload script |
| `requirements.txt` | Python dependencies |

## Testing

Test the server manually:

```bash
# Test embeddings
python embeddings.py

# Test Qdrant connection
python qdrant_store.py

# Test ingestion
python ingest.py ../datasets/bandar_frd/document.txt --collection test_collection

# Test full search
python -c "
from embeddings import embed_text
from qdrant_store import get_qdrant_client, search

client = get_qdrant_client()
query = 'payment options'
embedding = embed_text(query)
results = search(client, 'bandar_frd', embedding, top_k=3)
for r in results:
    print(f'Score: {r.score:.3f}')
    print(f'Chunk: {r.metadata.get(\"chunk_index\", \"N/A\")} | Tokens: {r.metadata.get(\"token_count\", \"N/A\")}')
    print(f'Text: {r.text[:200]}...')
    print('---')
"
```

## Troubleshooting

**"Qdrant connection failed: QDRANT_URL not set"**
- Ensure `QDRANT_URL` environment variable is set with Qdrant Cloud URL

**"Failed to generate embedding"**
- Ensure dependencies are installed: `pip install -r requirements.txt`
- If using a fresh environment, run `python embeddings.py` once to warm the local model download

**"Collection '{name}' not found"**
- Ingest documents first: `python ingest.py ../datasets/bandar_frd/document.txt --collection bandar_frd`
- Verify `RAG_COLLECTION` environment variable matches the ingested collection name

**"Failed to connect to Qdrant"**
- Check Qdrant Cloud cluster is running
- Verify URL is correct and includes `https://`
- Check API key is valid

**"Search failed"**
- Verify collection has been populated with vectors
- Check Qdrant Cloud connection status
- Ensure query is not empty
