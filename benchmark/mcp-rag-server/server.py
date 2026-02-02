#!/usr/bin/env python3
"""
MCP RAG Server

Exposes a vector search tool via the Model Context Protocol (MCP).
Connects to Qdrant Cloud for vector similarity search.
"""

import os
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from embeddings import embed_text
from qdrant_client import get_qdrant_client, search, SearchResult, DEFAULT_COLLECTION


# Initialize MCP server
server = Server("rag-server")


# Configuration from environment
COLLECTION_NAME = os.environ.get("RAG_COLLECTION", DEFAULT_COLLECTION)


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


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="rag_search",
            description=(
                "Search the document for relevant content using semantic similarity. "
                "Returns the most relevant chunks from the document based on the query. "
                "Use this to find information about specific topics."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query - describe what you're looking for"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5, max: 10)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10
                    }
                },
                "required": ["query"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    if name == "rag_search":
        query = arguments.get("query", "")
        top_k = min(arguments.get("top_k", 5), 10)

        if not query:
            return [TextContent(type="text", text="Error: query is required")]

        try:
            # Generate embedding for query
            try:
                query_embedding = embed_text(query)
            except Exception as e:
                error_msg = str(e)
                if "OPENAI_API_KEY" in error_msg:
                    return [TextContent(type="text", text=f"Error: OpenAI API key not set. {error_msg}")]
                return [TextContent(type="text", text=f"Error: Failed to generate embedding: {error_msg}")]

            # Connect to Qdrant
            try:
                client = get_qdrant_client()
            except ValueError as e:
                return [TextContent(type="text", text=f"Error: Qdrant connection failed: {str(e)}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: Failed to connect to Qdrant: {str(e)}")]

            # Check if collection exists
            try:
                collections = client.get_collections().collections
                collection_exists = any(c.name == COLLECTION_NAME for c in collections)
                if not collection_exists:
                    return [TextContent(type="text", text=f"Error: Collection '{COLLECTION_NAME}' not found. Available collections: {[c.name for c in collections]}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: Failed to check collection: {str(e)}")]

            # Perform search
            try:
                results = search(
                    client,
                    COLLECTION_NAME,
                    query_embedding,
                    top_k=top_k
                )
            except Exception as e:
                return [TextContent(type="text", text=f"Error: Search failed: {str(e)}")]

            # Format results
            formatted = format_results(results)
            return [TextContent(type="text", text=formatted)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: Unexpected error during search: {str(e)}")]

    else:
        return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
