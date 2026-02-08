#!/usr/bin/env python3
"""
Text embedding utilities using sentence-transformers.
"""

from typing import List
from sentence_transformers import SentenceTransformer


# Default embedding model
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # Dimension for all-MiniLM-L6-v2

# Lazy-loaded model singleton
_model = None


def _get_model(model_name: str = DEFAULT_MODEL) -> SentenceTransformer:
    """Get or create the SentenceTransformer model (singleton)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(model_name)
    return _model


def embed_text(
    text: str,
    model: str = DEFAULT_MODEL,
) -> List[float]:
    """
    Generate embedding for a single text.

    Args:
        text: Text to embed
        model: Model name

    Returns:
        List of floats representing the embedding vector
    """
    m = _get_model(model)
    embedding = m.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_texts(
    texts: List[str],
    model: str = DEFAULT_MODEL,
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batch.

    Args:
        texts: List of texts to embed
        model: Model name

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    m = _get_model(model)
    embeddings = m.encode(texts, normalize_embeddings=True, batch_size=64)
    return [e.tolist() for e in embeddings]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    import math

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


if __name__ == "__main__":
    test_text = "What are the payment options for booking?"
    print(f"Embedding text: {test_text}")

    try:
        embedding = embed_text(test_text)
        print(f"Embedding dimension: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
    except Exception as e:
        print(f"Error: {e}")
