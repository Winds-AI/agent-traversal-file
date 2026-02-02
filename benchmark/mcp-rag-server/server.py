#!/usr/bin/env python3
"""
MCP RAG Server

Exposes a vector search tool via the Model Context Protocol (MCP).
Connects to Qdrant Cloud for vector similarity search.
"""

import os
import asyncio
import json
from typing import Optional

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
        # Include metadata if present
        meta_info = ""
        if r.metadata:
            section_id = r.metadata.get("section_id", "")
            if section_id:
                meta_info = f" [Section: {section_id}]"

        formatted.append(
            f"## Result {i} (Score: {r.score:.3f}){meta_info}\n\n{r.text}\n"
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
        ),
        Tool(
            name="rag_info",
            description="Get information about the document collection (number of chunks, etc.)",
            inputSchema={
                "type": "object",
                "properties": {}
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
            query_embedding = embed_text(query)

            # Search Qdrant
            client = get_qdrant_client()
            results = search(
                client,
                COLLECTION_NAME,
                query_embedding,
                top_k=top_k
            )

            # Format results
            formatted = format_results(results)

            return [TextContent(type="text", text=formatted)]

        except Exception as e:
            return [TextContent(type="text", text=f"Search error: {str(e)}")]

    elif name == "rag_info":
        try:
            from qdrant_client import get_collection_info
            client = get_qdrant_client()
            info = get_collection_info(client, COLLECTION_NAME)

            return [TextContent(
                type="text",
                text=f"Collection: {COLLECTION_NAME}\n" + json.dumps(info, indent=2)
            )]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


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
