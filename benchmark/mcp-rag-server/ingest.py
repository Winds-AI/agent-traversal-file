#!/usr/bin/env python3
"""
Document ingestion script for RAG benchmark.

Chunks documents and uploads embeddings to Qdrant Cloud.
"""

import argparse
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

try:
    import tiktoken
except ImportError:
    tiktoken = None

from embeddings import embed_texts, EMBEDDING_DIMENSION
from qdrant_client import (
    get_qdrant_client,
    create_collection,
    upsert_vectors,
    get_collection_info,
    DEFAULT_COLLECTION
)


@dataclass
class Chunk:
    """A document chunk for embedding."""
    id: str
    text: str
    metadata: Dict[str, Any]


def chunk_text_by_tokens(
    text: str,
    chunk_size: int = 2048,
    overlap: int = 100,
    source: str = "document"
) -> List[Chunk]:
    """
    Chunk text into segments based on token count with overlap.

    Args:
        text: Full document text
        chunk_size: Target size of each chunk in tokens
        overlap: Number of tokens to overlap between chunks
        source: Source identifier for metadata

    Returns:
        List of Chunk objects
    """
    chunks = []

    # Use tiktoken for accurate token counting
    if tiktoken is None:
        raise ImportError("tiktoken is required for token-based chunking. Install it with: pip install tiktoken")

    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)

    chunk_idx = 0
    stride = chunk_size - overlap

    for i in range(0, len(tokens), stride):
        # Don't create a chunk that's too small at the end
        if i + chunk_size > len(tokens) and i > 0:
            break

        chunk_tokens = tokens[i:i + chunk_size]
        chunk_text = encoding.decode(chunk_tokens)

        if chunk_text.strip():
            chunks.append(Chunk(
                id=f"{source}_chunk_{chunk_idx}",
                text=chunk_text.strip(),
                metadata={
                    "source": source,
                    "chunk_index": chunk_idx,
                    "token_count": len(chunk_tokens),
                    "char_count": len(chunk_text)
                }
            ))
            chunk_idx += 1

    return chunks


def ingest_document(
    file_path: Path,
    collection_name: str = DEFAULT_COLLECTION,
    recreate: bool = False
) -> Dict[str, Any]:
    """
    Ingest a document into Qdrant.

    Args:
        file_path: Path to text document
        collection_name: Qdrant collection name
        recreate: If True, delete and recreate collection

    Returns:
        Ingestion statistics
    """
    print(f"Ingesting: {file_path}")

    # Read and chunk document
    with open(file_path) as f:
        text = f.read()
    chunks = chunk_text_by_tokens(text, chunk_size=2048, overlap=100, source=file_path.stem)

    print(f"Created {len(chunks)} chunks")

    # Generate embeddings in batches of 10 chunks
    print("Generating embeddings...")
    texts = [c.text for c in chunks]
    batch_size = 10
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = embed_texts(batch)
        all_embeddings.extend(batch_embeddings)
        print(f"  Processed {min(i + batch_size, len(texts))}/{len(texts)} chunks")

    print(f"Generated {len(all_embeddings)} embeddings")

    # Connect to Qdrant
    print("Connecting to Qdrant...")
    client = get_qdrant_client()

    # Create collection if needed
    created = create_collection(client, collection_name, recreate=recreate)
    if created:
        print(f"Created collection: {collection_name}")
    else:
        print(f"Using existing collection: {collection_name}")

    # Upload vectors
    print("Uploading vectors...")
    ids = [c.id for c in chunks]
    metadata = [c.metadata for c in chunks]
    count = upsert_vectors(client, collection_name, ids, all_embeddings, texts, metadata)

    # Get collection info
    info = get_collection_info(client, collection_name)

    result = {
        "file": str(file_path),
        "chunks": len(chunks),
        "vectors_uploaded": count,
        "collection": info
    }

    print(f"Done! Uploaded {count} vectors")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Ingest documents into Qdrant for RAG benchmark"
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Text document file to ingest (.txt)"
    )
    parser.add_argument(
        "--collection", "-c",
        default=DEFAULT_COLLECTION,
        help=f"Qdrant collection name (default: {DEFAULT_COLLECTION})"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate collection"
    )

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        return 1

    try:
        result = ingest_document(
            args.file,
            collection_name=args.collection,
            recreate=args.recreate
        )
        print("\nIngestion complete:")
        for k, v in result.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
