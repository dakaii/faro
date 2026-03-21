"""
RAG ingestion: PDF → chunk → embed → Neo4j ReportChunk nodes.
Best practice: chunk with overlap, batch writes, ensure vector index exists first.
"""
import re
from typing import Any

from app.core.config import settings
from app.services.embeddings import embed_text
from app.services.neo4j_client import (
    RAG_CHUNK_LABEL,
    RAG_EMBEDDING_PROP,
    RAG_TEXT_PROP,
    ensure_rag_vector_index,
    get_driver,
)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks (chars)."""
    if not text or chunk_size <= 0:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if overlap < chunk_size else end
    return chunks


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract raw text from PDF bytes using pypdf."""
    from pypdf import PdfReader
    from io import BytesIO

    reader = PdfReader(BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    text = "\n".join(parts)
    # Normalize whitespace
    return re.sub(r"\s+", " ", text).strip()


def ingest_document_to_rag(
    app: Any,
    text: str,
    *,
    source: str = "",
    chunk_size: int = 500,
    overlap: int = 50,
) -> int:
    """
    Complete document ingestion pipeline for RAG system.
    
    Process:
    1. Validate prerequisites (database connection, embedding API)
    2. Ensure vector index exists in Neo4j
    3. Chunk document text with overlap
    4. Generate embeddings for each chunk
    5. Write chunks with embeddings to Neo4j as ReportChunk nodes
    
    Args:
        app: FastAPI application instance (for database access)
        text: Raw document text to ingest
        source: Source identifier for the document (optional)
        chunk_size: Maximum characters per chunk (default: 500)
        overlap: Character overlap between chunks (default: 50)
        
    Returns:
        Number of chunks successfully written to database
    """
    # 1. Validate prerequisites
    if not _has_database_access(app):
        return 0
        
    if not _has_embedding_api_access():
        return 0

    driver = get_driver(app) if app else get_driver()
    
    # 2. Ensure vector index exists
    if not ensure_rag_vector_index(driver):
        return 0

    # 3. Chunk the document text
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        return 0

    # 4. Generate embeddings for chunks
    embedded_chunks = _create_embedded_chunks(chunks, source)
    if not embedded_chunks:
        return 0

    # 5. Write to Neo4j database
    try:
        with driver.session() as session:
            return session.execute_write(_write_chunks_to_db, embedded_chunks)
    except Exception:
        return 0


def _has_database_access(app: Any) -> bool:
    """Check if Neo4j database connection is available."""
    driver = get_driver(app) if app else get_driver()
    return driver is not None


def _has_embedding_api_access() -> bool:
    """Check if embedding API (OpenAI or compatible) is configured."""
    return bool(settings.openai_api_key or settings.openai_base_url)


def _create_embedded_chunks(chunks: list[str], source: str) -> list[dict]:
    """Generate embeddings for text chunks and prepare for database storage."""
    embeddings = [embed_text(chunk) for chunk in chunks]
    
    # Filter out chunks where embedding generation failed
    return [
        {"text": chunk, "embedding": embedding, "source": source}
        for chunk, embedding in zip(chunks, embeddings)
        if embedding is not None
    ]


def _write_chunks_to_db(tx: Any, embedded_chunks: list[dict]) -> int:
    """Write embedded chunks to Neo4j as ReportChunk nodes."""
    count = 0
    
    for chunk_data in embedded_chunks:
        tx.run(
            f"""
            CREATE (n:{RAG_CHUNK_LABEL})
            SET n.{RAG_TEXT_PROP} = $text,
                n.{RAG_EMBEDDING_PROP} = $embedding,
                n.source = $source
            """,
            text=chunk_data["text"],
            embedding=chunk_data["embedding"],
            source=chunk_data["source"],
        ).consume()
        count += 1
        
    return count
