#!/usr/bin/env python3
"""
Qdrant Cloud client wrapper for vector storage and retrieval.
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct


# Default settings
DEFAULT_COLLECTION = "bandar_frd"
VECTOR_SIZE = 1536  # text-embedding-3-small dimension


@dataclass
class SearchResult:
    """A single search result."""
    id: str
    score: float
    text: str
    metadata: Dict[str, Any]


def get_qdrant_client(
    url: Optional[str] = None,
    api_key: Optional[str] = None
) -> QdrantClient:
    """
    Get a Qdrant client connected to Qdrant Cloud.

    Args:
        url: Qdrant Cloud URL (uses QDRANT_URL env var if not provided)
        api_key: Qdrant API key (uses QDRANT_API_KEY env var if not provided)

    Returns:
        Connected QdrantClient instance
    """
    url = url or os.environ.get("QDRANT_URL")
    api_key = api_key or os.environ.get("QDRANT_API_KEY")

    if not url:
        raise ValueError("QDRANT_URL not set")

    return QdrantClient(
        url=url,
        api_key=api_key,
        timeout=30
    )


def create_collection(
    client: QdrantClient,
    collection_name: str = DEFAULT_COLLECTION,
    vector_size: int = VECTOR_SIZE,
    recreate: bool = False
) -> bool:
    """
    Create a collection in Qdrant.

    Args:
        client: Qdrant client
        collection_name: Name of the collection
        vector_size: Dimension of vectors
        recreate: If True, delete existing collection first

    Returns:
        True if collection was created, False if it already existed
    """
    # Check if collection exists
    collections = client.get_collections().collections
    exists = any(c.name == collection_name for c in collections)

    if exists:
        if recreate:
            client.delete_collection(collection_name)
        else:
            return False

    # Create collection
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE
        )
    )

    return True


def upsert_vectors(
    client: QdrantClient,
    collection_name: str,
    ids: List[str],
    vectors: List[List[float]],
    texts: List[str],
    metadata: Optional[List[Dict[str, Any]]] = None
) -> int:
    """
    Insert or update vectors in the collection.

    Args:
        client: Qdrant client
        collection_name: Name of the collection
        ids: Unique IDs for each vector
        vectors: List of embedding vectors
        texts: Original text for each vector
        metadata: Optional metadata for each vector

    Returns:
        Number of vectors upserted
    """
    if metadata is None:
        metadata = [{} for _ in ids]

    points = [
        PointStruct(
            id=i,  # Qdrant wants numeric IDs, we'll store string ID in payload
            vector=vector,
            payload={
                "id": str_id,
                "text": text,
                **meta
            }
        )
        for i, (str_id, vector, text, meta) in enumerate(zip(ids, vectors, texts, metadata))
    ]

    # Upsert in batches
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(
            collection_name=collection_name,
            points=batch
        )

    return len(points)


def search(
    client: QdrantClient,
    collection_name: str,
    query_vector: List[float],
    top_k: int = 5,
    score_threshold: Optional[float] = None
) -> List[SearchResult]:
    """
    Search for similar vectors.

    Args:
        client: Qdrant client
        collection_name: Name of the collection
        query_vector: Query embedding vector
        top_k: Number of results to return
        score_threshold: Minimum similarity score

    Returns:
        List of SearchResult objects
    """
    results = client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=top_k,
        score_threshold=score_threshold
    )

    return [
        SearchResult(
            id=str(hit.payload.get("id", hit.id)),
            score=hit.score,
            text=hit.payload.get("text", ""),
            metadata={k: v for k, v in hit.payload.items() if k not in ("id", "text")}
        )
        for hit in results
    ]


def get_collection_info(
    client: QdrantClient,
    collection_name: str = DEFAULT_COLLECTION
) -> Dict[str, Any]:
    """Get information about a collection."""
    try:
        info = client.get_collection(collection_name)
        return {
            "name": collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.value
        }
    except Exception as e:
        return {"error": str(e)}


def delete_collection(
    client: QdrantClient,
    collection_name: str = DEFAULT_COLLECTION
) -> bool:
    """Delete a collection."""
    try:
        client.delete_collection(collection_name)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # Test connection
    print("Testing Qdrant connection...")

    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        print(f"Connected! Found {len(collections.collections)} collections:")
        for c in collections.collections:
            print(f"  - {c.name}")
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Make sure QDRANT_URL and QDRANT_API_KEY are set")
