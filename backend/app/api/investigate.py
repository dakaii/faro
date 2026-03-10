from fastapi import APIRouter, Request, HTTPException

from app.models.schemas import InvestigateResponse, WalletRequest
from app.services.etherscan import EtherscanFetcher
from app.services.neo4j_client import get_graph_context

router = APIRouter()


@router.post("/investigate", response_model=InvestigateResponse)
async def investigate_wallet(req: WalletRequest, request: Request) -> InvestigateResponse:
    """
    Investigate a wallet: fetch on-chain data, (optional) graph + RAG context,
    then synthesize risk score and evidence. LLM integration in Sprint 2.
    """
    address = req.address.strip()
    if not address or not address.startswith("0x"):
        raise HTTPException(status_code=400, detail="Invalid wallet address")

    fetcher = EtherscanFetcher()
    wallet_story = fetcher.get_wallet_summary(address, chain_id=req.chain_id)
    graph_summary = get_graph_context(address, request.app)

    # Placeholder: no LLM yet – return a simple heuristic so the pipeline is testable
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
        if "Graph: wallet is within" in graph_summary and "0" not in graph_summary:
            risk_score = 85
            evidence.append(graph_summary)
        else:
            evidence.append(graph_summary)

    summary = (
        "Placeholder report (LLM not connected). "
        "Connect an LLM in Sprint 2 to synthesize risk from wallet story and RAG."
    )
    if risk_score >= 70:
        summary = "Higher risk indicators present. Review evidence and connect LLM for full analysis."

    return InvestigateResponse(
        address=address,
        risk_score=min(risk_score, 100),
        summary=summary,
        evidence=evidence,
    )
