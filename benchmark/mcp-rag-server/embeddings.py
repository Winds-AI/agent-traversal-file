#!/usr/bin/env python3
"""
Text embedding utilities using OpenAI's embedding models.
"""

import os
from typing import List, Optional
from openai import OpenAI


# Default embedding model
DEFAULT_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # Dimension for text-embedding-3-small


def get_client(api_key: Optional[str] = None) -> OpenAI:
    """Get an OpenAI client."""
    return OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))


def embed_text(
    text: str,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None
) -> List[float]:
    """
    Generate embedding for a single text.

    Args:
        text: Text to embed
        model: OpenAI embedding model name
        api_key: Optional API key (uses OPENAI_API_KEY env var if not provided)

    Returns:
        List of floats representing the embedding vector
    """
    client = get_client(api_key)

    response = client.embeddings.create(
        model=model,
        input=text
    )

    return response.data[0].embedding


def embed_texts(
    texts: List[str],
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batch.

    Args:
        texts: List of texts to embed
        model: OpenAI embedding model name
        api_key: Optional API key

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    client = get_client(api_key)

    # OpenAI supports batching up to 2048 texts
    # Process in batches if needed
    batch_size = 2000
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            model=model,
            input=batch
        )
        # Sort by index to maintain order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        all_embeddings.extend([d.embedding for d in sorted_data])

    return all_embeddings


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Cosine similarity score (0 to 1 for normalized vectors)
    """
    import math

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


if __name__ == "__main__":
    # Test embedding
    test_text = "What are the payment options for booking?"
    print(f"Embedding text: {test_text}")

    try:
        embedding = embed_text(test_text)
        print(f"Embedding dimension: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure OPENAI_API_KEY is set")
