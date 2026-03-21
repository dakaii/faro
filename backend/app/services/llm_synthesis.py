"""
LLM synthesis: wallet story + graph context + RAG chunks → risk score, summary, evidence.
Uses any OpenAI-compatible API (OpenAI, OpenRouter, self-hosted). Returns None for heuristic fallback when unset.
"""
from app.core.config import settings
from app.core.logging import ServiceLogger

logger = ServiceLogger("llm_synthesis")


class LLMSynthesisError(Exception):
    """Raised when LLM synthesis fails."""
    pass


def _llm_client():
    """Build OpenAI-compatible client (base_url when set = OpenRouter / self-hosted)."""
    from openai import OpenAI

    logger.debug("creating_llm_client", 
                 has_api_key=bool(settings.openai_api_key),
                 base_url=settings.openai_base_url)

    kwargs = {"api_key": settings.openai_api_key or "no-key"}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url.rstrip("/")
    return OpenAI(**kwargs)


def synthesize_risk(
    address: str,
    wallet_story: str,
    graph_summary: str,
    rag_chunks: list[str],
) -> tuple[int, str, list[str]] | None:
    """
    Call LLM to produce risk_score (0–100), summary, and evidence list.
    Returns None if neither API key nor base_url is configured, or on error (caller uses heuristic).
    """
    if not settings.openai_api_key and not settings.openai_base_url:
        logger.debug("llm_synthesis_skipped", reason="no api credentials")
        return None

    logger.info("synthesizing_risk_with_llm",
                address=address,
                wallet_story_length=len(wallet_story),
                graph_summary_length=len(graph_summary),
                rag_chunks_count=len(rag_chunks))

    rag_block = ""
    if rag_chunks:
        rag_block = "Relevant threat intel excerpts:\n" + "\n---\n".join(rag_chunks[:5])
        logger.debug("including_rag_context", chunks_count=len(rag_chunks))

    prompt = f"""You are a blockchain forensic analyst. Given the following data about a wallet, produce a risk assessment.

Wallet address: {address}

On-chain (Etherscan) summary:
{wallet_story}

Graph context (Neo4j – proximity to known bad actors/mixers):
{graph_summary}

{rag_block}

Respond with exactly this JSON (no markdown, no extra text):
{{"risk_score": <0-100 integer>, "summary": "<2-3 sentence summary>", "evidence": ["<bullet 1>", "<bullet 2>", "<at least 3 bullets>"]}}
Risk score: 0 = low, 40-69 = medium, 70+ = high. Evidence must be specific and cite the data above."""

    try:
        logger.debug("calling_llm_api", 
                     model=settings.openai_llm_model,
                     prompt_length=len(prompt))
        
        client = _llm_client()
        resp = client.chat.completions.create(
            model=settings.openai_llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        
        content = (resp.choices[0].message.content or "").strip()
        logger.debug("llm_response_received", content_length=len(content))
        
        # Strip markdown code fence if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            logger.debug("stripped_markdown_fence")
        
        import json
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("llm_json_parsing_failed", 
                        content=content[:200], 
                        error=str(e))
            return None
            
        score = max(0, min(100, int(data.get("risk_score", 0))))
        summary = str(data.get("summary", "")) or "No summary produced."
        evidence = list(data.get("evidence", []))
        
        if not isinstance(evidence, list):
            evidence = [str(evidence)]
        evidence = [str(e) for e in evidence[:10]]
        
        logger.info("llm_synthesis_completed_successfully",
                    address=address,
                    risk_score=score,
                    evidence_count=len(evidence),
                    model=settings.openai_llm_model)
        
        return (score, summary, evidence)
        
    except Exception as e:
        logger.error("llm_synthesis_failed",
                     address=address,
                     error=e,
                     model=settings.openai_llm_model)
        # Return None for graceful fallback to heuristic
        return None
