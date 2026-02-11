#!/usr/bin/env python3
"""
MCP RAG Server

Exposes a vector search tool via the Model Context Protocol (MCP).
Connects to Qdrant Cloud for vector similarity search.

Usage:
    # Stdio mode (default, for local MCP)
    python server.py

    # SSE mode (persistent server for benchmarking)
    python server.py --transport sse --port 8808
"""

import os
import sys
import argparse
import threading
from dotenv import load_dotenv

load_dotenv()

# Ensure local modules are importable regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

from qdrant_store import get_qdrant_client, search, SearchResult, DEFAULT_COLLECTION


# Configuration from environment
COLLECTION_NAME = os.environ.get("RAG_COLLECTION", DEFAULT_COLLECTION)
RAG_PORT = int(os.environ.get("RAG_PORT", "8808"))

# Initialize MCP server
mcp = FastMCP("rag-server", host="0.0.0.0", port=RAG_PORT)

# Pre-load embedding model in background thread so it's ready when first tool call comes
_embed_fn = None
_embed_lock = threading.Event()

def _warmup_model():
    global _embed_fn
    from embeddings import embed_text
    # Trigger model load by running a dummy embed
    embed_text("warmup")
    _embed_fn = embed_text
    _embed_lock.set()
    print("[rag-server] Embedding model loaded and ready", flush=True)

_warmup_thread = threading.Thread(target=_warmup_model, daemon=True)
_warmup_thread.start()

def _get_embed_fn():
    _embed_lock.wait()  # Block until model is loaded
    return _embed_fn


def format_results(results: list[SearchResult]) -> str:
    """Format search results as readable text."""
    if not results:
        return "No relevant content found."

    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"## Result {i} (Score: {r.score:.3f})\n\n{r.text}\n"
        )

    return "\n---\n".join(formatted)


@mcp.tool()
def rag_search(query: str, top_k: int = 5) -> str:
    """Search the document for relevant content using semantic similarity.
    Returns the most relevant chunks from the document based on the query.
    Use this to find information about specific topics.

    Args:
        query: The search query - describe what you're looking for
        top_k: Number of results to return (default: 5, max: 10)
    """
    if not query:
        return "Error: query is required"

    top_k = min(top_k, 10)

    try:
        query_embedding = _get_embed_fn()(query)
    except Exception as e:
        return f"Error: Failed to generate embedding: {e}"

    try:
        client = get_qdrant_client()
    except Exception as e:
        return f"Error: Qdrant connection failed: {e}"

    try:
        results = search(
            client,
            COLLECTION_NAME,
            query_embedding,
            top_k=top_k
        )
    except Exception as e:
        return f"Error: Search failed: {e}"

    return format_results(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP RAG Server")
    parser.add_argument(
        "--transport", "-t",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport mode (default: stdio)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=RAG_PORT,
        help=f"Port for SSE mode (default: {RAG_PORT})"
    )
    args = parser.parse_args()

    if args.transport in ("sse", "streamable-http"):
        mcp.settings.port = args.port
        print(f"[rag-server] Starting {args.transport} server on port {args.port}...", flush=True)
        print(f"[rag-server] Embedding model loading in background...", flush=True)

    mcp.run(transport=args.transport)
