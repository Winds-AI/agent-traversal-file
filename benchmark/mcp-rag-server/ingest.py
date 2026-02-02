#!/usr/bin/env python3
"""
Document ingestion script for RAG benchmark.

Chunks documents and uploads embeddings to Qdrant Cloud.
"""

import re
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

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


def chunk_plain_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    source: str = "document"
) -> List[Chunk]:
    """
    Chunk plain text into overlapping segments.

    Args:
        text: Full document text
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        source: Source identifier for metadata

    Returns:
        List of Chunk objects
    """
    chunks = []

    # Split into paragraphs first
    paragraphs = text.split("\n\n")

    current_chunk = ""
    chunk_idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If adding this paragraph would exceed chunk size
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            # Save current chunk
            chunks.append(Chunk(
                id=f"{source}_chunk_{chunk_idx}",
                text=current_chunk.strip(),
                metadata={
                    "source": source,
                    "chunk_index": chunk_idx,
                    "char_count": len(current_chunk)
                }
            ))
            chunk_idx += 1

            # Start new chunk with overlap
            overlap_start = max(0, len(current_chunk) - chunk_overlap)
            current_chunk = current_chunk[overlap_start:] + "\n\n" + para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(Chunk(
            id=f"{source}_chunk_{chunk_idx}",
            text=current_chunk.strip(),
            metadata={
                "source": source,
                "chunk_index": chunk_idx,
                "char_count": len(current_chunk)
            }
        ))

    return chunks


def chunk_iatf_document(file_path: Path) -> List[Chunk]:
    """
    Chunk an IATF document by sections.

    Each IATF section becomes a separate chunk, preserving structure.

    Args:
        file_path: Path to IATF file

    Returns:
        List of Chunk objects, one per IATF section
    """
    with open(file_path) as f:
        content = f.read()

    chunks = []
    source = file_path.stem

    # Find all sections using regex
    # IATF sections are delimited by {#section-id} ... {/section-id}
    section_pattern = r'\{#([^}|]+)(?:\|[^}]*)?\}(.*?)\{/\1\}'

    for match in re.finditer(section_pattern, content, re.DOTALL):
        section_id = match.group(1).strip()
        section_content = match.group(2).strip()

        # Clean up the content
        # Remove @summary lines for cleaner text
        lines = section_content.split("\n")
        cleaned_lines = [l for l in lines if not l.strip().startswith("@summary:")]
        cleaned_content = "\n".join(cleaned_lines).strip()

        if cleaned_content:
            chunks.append(Chunk(
                id=f"{source}_{section_id}",
                text=cleaned_content,
                metadata={
                    "source": source,
                    "section_id": section_id,
                    "char_count": len(cleaned_content),
                    "format": "iatf"
                }
            ))

    # If no sections found, fall back to plain text chunking
    if not chunks:
        print("Warning: No IATF sections found, using plain text chunking")
        return chunk_plain_text(content, source=source)

    return chunks


def ingest_document(
    file_path: Path,
    collection_name: str = DEFAULT_COLLECTION,
    recreate: bool = False
) -> Dict[str, Any]:
    """
    Ingest a document into Qdrant.

    Args:
        file_path: Path to document (txt or iatf)
        collection_name: Qdrant collection name
        recreate: If True, delete and recreate collection

    Returns:
        Ingestion statistics
    """
    print(f"Ingesting: {file_path}")

    # Chunk document
    if file_path.suffix == ".iatf":
        chunks = chunk_iatf_document(file_path)
    else:
        with open(file_path) as f:
            text = f.read()
        chunks = chunk_plain_text(text, source=file_path.stem)

    print(f"Created {len(chunks)} chunks")

    # Generate embeddings
    print("Generating embeddings...")
    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)
    print(f"Generated {len(embeddings)} embeddings")

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
    count = upsert_vectors(client, collection_name, ids, embeddings, texts, metadata)

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
        help="Document file to ingest (.txt or .iatf)"
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
