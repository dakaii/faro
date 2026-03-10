from fastapi import APIRouter, Request, HTTPException

from app.models.schemas import InvestigateResponse, WalletRequest
from app.services.etherscan import EtherscanFetcher
from app.services.graph_ingest import ingest_wallet_transactions
from app.services.neo4j_client import get_graph_context, get_rag_context
from app.services.llm_synthesis import synthesize_risk

router = APIRouter()


def _heuristic_risk(wallet_story: str, graph_summary: str) -> tuple[int, str, list[str]]:
    """Fallback when LLM is not configured."""
    risk_score = 0
    evidence: list[str] = []

    if "Error fetching" in wallet_story:
        risk_score = 50
        evidence.append("Could not fetch transaction history; unable to assess.")
    elif "No transactions found" in wallet_story:
        risk_score = 65
        evidence.append("New or empty wallet (no history) – higher baseline risk.")
    else:
        evidence.append("Transaction history retrieved successfully.")
        evidence.append(graph_summary)
        if "Graph: wallet is within" in graph_summary and "0" not in graph_summary:
            risk_score = 85

    summary = (
        "Placeholder report (LLM not connected). "
        "Set OPENAI_API_KEY to synthesize risk from wallet story and RAG."
    )
    if risk_score >= 70:
        summary = "Higher risk indicators present. Review evidence and set OPENAI_API_KEY for full analysis."
    return (min(risk_score, 100), summary, evidence)


@router.post("/investigate", response_model=InvestigateResponse)
async def investigate_wallet(req: WalletRequest, request: Request) -> InvestigateResponse:
    """
    Investigate a wallet: fetch on-chain data, ingest to graph, (optional) graph + RAG context,
    then synthesize risk via LLM when configured, else heuristic.
    """
    address = req.address.strip()
    if not address or not address.startswith("0x") or len(address) != 42:
        raise HTTPException(status_code=400, detail="Invalid wallet address (0x + 40 hex chars)")

    fetcher = EtherscanFetcher()
    wallet_story, txs = fetcher.get_tx_list_ok(address, chain_id=req.chain_id)
    ingest_wallet_transactions(request.app, address, req.chain_id, txs)
    graph_summary = get_graph_context(address, request.app)

    # RAG: behaviour summary for semantic search (first ~500 chars of story)
    behaviour_summary = (wallet_story[:500] + ("..." if len(wallet_story) > 500 else "")) or address
    rag_chunks = get_rag_context(behaviour_summary, request.app, top_k=5)

    llm_result = synthesize_risk(address, wallet_story, graph_summary, rag_chunks)
    if llm_result is not None:
        risk_score, summary, evidence = llm_result
    else:
        risk_score, summary, evidence = _heuristic_risk(wallet_story, graph_summary)

    return InvestigateResponse(
        address=address,
        risk_score=min(risk_score, 100),
        summary=summary,
        evidence=evidence,
    )
