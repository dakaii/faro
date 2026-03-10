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
    Chunk text, embed each chunk, write ReportChunk nodes to Neo4j.
    Ensures vector index exists. Returns number of chunks written.
    """
    driver = get_driver(app) if app else get_driver()
    if not driver:
        return 0
    if not settings.openai_api_key and not settings.openai_base_url:
        return 0

    if not ensure_rag_vector_index(driver):
        return 0

    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        return 0

    embeddings = [embed_text(c) for c in chunks]
    rows = [
        {"text": c, "embedding": e, "source": source}
        for c, e in zip(chunks, embeddings)
        if e is not None
    ]
    if not rows:
        return 0

    def _write(tx: Any) -> int:
        count = 0
        for row in rows:
            tx.run(
                f"""
                CREATE (n:{RAG_CHUNK_LABEL})
                SET n.{RAG_TEXT_PROP} = $text,
                    n.{RAG_EMBEDDING_PROP} = $embedding,
                    n.source = $source
                """,
                text=row["text"],
                embedding=row["embedding"],
                source=row["source"],
            ).consume()
            count += 1
        return count

    try:
        with driver.session() as session:
            return session.execute_write(_write)
    except Exception:
        return 0
