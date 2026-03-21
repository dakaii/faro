"""
Document ingestion for RAG: upload PDFs to be chunked, embedded, and stored in Neo4j.
"""
from typing import Annotated
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Depends

from app.core.auth import User, RequireIngest
from app.middleware.rate_limit import strict_rate_limit
from app.services.rag_ingest import extract_text_from_pdf, ingest_document_to_rag

router = APIRouter()


@router.post("/ingest-doc")
async def ingest_doc(
    request: Request,
    file: UploadFile = File(...),
    source: str = Form(""),
    current_user: Annotated[User, Depends(RequireIngest)] = None,
    rate_limit: bool = Depends(strict_rate_limit)
) -> dict:
    """
    Upload a PDF; extract text, chunk, embed, and write to Neo4j ReportChunk nodes.
    Requires OPENAI_API_KEY and Neo4j. Returns number of chunks ingested.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF file required")
    try:
        raw = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}") from e

    text = extract_text_from_pdf(raw)
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from PDF")

    source_label = (source or file.filename or "").strip() or "upload"
    n = ingest_document_to_rag(request.app, text, source=source_label)
    return {"ingested": n, "source": source_label}
