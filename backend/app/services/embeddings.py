"""
Text embeddings for RAG. Uses any OpenAI-compatible API (OpenAI, OpenRouter, self-hosted).
Returns None when API key is not configured or on error.
"""
from app.core.config import settings
from app.core.logging import ServiceLogger

logger = ServiceLogger("embeddings")


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    pass


def _embed_client():
    """Build OpenAI-compatible client (base_url when set = OpenRouter / self-hosted)."""
    from openai import OpenAI

    logger.debug("creating_embedding_client", 
                 has_api_key=bool(settings.openai_api_key),
                 base_url=settings.openai_base_url)
    
    kwargs = {"api_key": settings.openai_api_key or "no-key"}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url.rstrip("/")
    return OpenAI(**kwargs)


def embed_text(text: str) -> list[float] | None:
    """
    Embed a single text. Returns None when neither api_key nor base_url is set,
    or on error (caller can fall back to no RAG).
    """
    if not (text := (text or "").strip()):
        logger.debug("embed_text_skipped", reason="empty text")
        return None
        
    if not settings.openai_api_key and not settings.openai_base_url:
        logger.debug("embed_text_skipped", reason="no api credentials")
        return None
        
    logger.debug("embedding_text", 
                 text_length=len(text),
                 model=settings.openai_embedding_model)
    
    try:
        client = _embed_client()
        kwargs = {
            "model": settings.openai_embedding_model,
            "input": text,
        }
        if settings.openai_embedding_dimensions > 0:
            kwargs["dimensions"] = settings.openai_embedding_dimensions
            
        logger.debug("calling_embedding_api", 
                     model=settings.openai_embedding_model,
                     dimensions=settings.openai_embedding_dimensions)
        
        resp = client.embeddings.create(**kwargs)
        embedding = resp.data[0].embedding
        
        logger.info("embedding_generated_successfully",
                    text_length=len(text),
                    embedding_dimensions=len(embedding),
                    model=settings.openai_embedding_model)
        
        return embedding
        
    except Exception as e:
        logger.error("embedding_generation_failed",
                     error=e,
                     text_length=len(text),
                     model=settings.openai_embedding_model)
        # Return None for graceful fallback (RAG becomes unavailable)
        return None


def embed_texts(texts: list[str]) -> list[list[float] | None]:
    """Embed multiple texts; each entry is embedding or None on failure."""
    if not texts:
        logger.debug("embed_texts_skipped", reason="empty text list")
        return []
        
    logger.info("embedding_multiple_texts", count=len(texts))
    
    results = []
    success_count = 0
    error_count = 0
    
    for i, text in enumerate(texts):
        embedding = embed_text(text)
        results.append(embedding)
        if embedding is not None:
            success_count += 1
        else:
            error_count += 1
    
    logger.info("embedding_batch_completed", 
                total_texts=len(texts),
                successful_embeddings=success_count,
                failed_embeddings=error_count)
    
    return results
