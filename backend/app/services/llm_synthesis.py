"""
LLM synthesis: wallet story + graph context + RAG chunks → risk score, summary, evidence.
Uses any OpenAI-compatible API (OpenAI, OpenRouter, self-hosted). Returns None for heuristic fallback when unset.
"""
from app.core.config import settings


def _llm_client():
    """Build OpenAI-compatible client (base_url when set = OpenRouter / self-hosted)."""
    from openai import OpenAI

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
        return None

    rag_block = ""
    if rag_chunks:
        rag_block = "Relevant threat intel excerpts:\n" + "\n---\n".join(rag_chunks[:5])

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
        client = _llm_client()
        resp = client.chat.completions.create(
            model=settings.openai_llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = (resp.choices[0].message.content or "").strip()
        # Strip markdown code fence if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        import json
        data = json.loads(content)
        score = max(0, min(100, int(data.get("risk_score", 0))))
        summary = str(data.get("summary", "")) or "No summary produced."
        evidence = list(data.get("evidence", []))
        if not isinstance(evidence, list):
            evidence = [str(evidence)]
        evidence = [str(e) for e in evidence[:10]]
        return (score, summary, evidence)
    except Exception:
        return None
