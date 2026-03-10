"""
Text embeddings for RAG. Uses any OpenAI-compatible API (OpenAI, OpenRouter, self-hosted).
Returns None when API key is not configured or on error.
"""
from app.core.config import settings


def _embed_client():
    """Build OpenAI-compatible client (base_url when set = OpenRouter / self-hosted)."""
    from openai import OpenAI

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
        return None
    if not settings.openai_api_key and not settings.openai_base_url:
        return None
    try:
        client = _embed_client()
        kwargs = {
            "model": settings.openai_embedding_model,
            "input": text,
        }
        if settings.openai_embedding_dimensions > 0:
            kwargs["dimensions"] = settings.openai_embedding_dimensions
        resp = client.embeddings.create(**kwargs)
        return resp.data[0].embedding
    except Exception:
        return None


def embed_texts(texts: list[str]) -> list[list[float] | None]:
    """Embed multiple texts; each entry is embedding or None on failure."""
    return [embed_text(t) for t in texts]
