from typing import Annotated
from fastapi import APIRouter, Request, HTTPException, Depends

from app.core.auth import User, RequireInvestigate
from app.middleware.rate_limit import strict_rate_limit
from app.models.schemas import InvestigateResponse, WalletRequest
from app.services.etherscan import EtherscanFetcher
from app.services.graph_ingest import ingest_wallet_transactions
from app.services.neo4j_client import get_graph_context, get_rag_context
from app.services.llm_synthesis import synthesize_risk

router = APIRouter()


def _heuristic_risk(wallet_story: str, graph_summary: str) -> tuple[int, str, list[str]]:
    """
    Fallback risk assessment when LLM is not configured.
    
    Args:
        wallet_story: Transaction history summary from Etherscan
        graph_summary: Graph context from Neo4j (proximity to known bad actors)
        
    Returns:
        Tuple of (risk_score, summary, evidence_list)
    """
    # Risk score constants
    FETCH_ERROR_SCORE = 50
    EMPTY_WALLET_SCORE = 65
    GRAPH_PROXIMITY_SCORE = 85
    HIGH_RISK_THRESHOLD = 70
    
    risk_score = 0
    evidence: list[str] = []

    # Assess based on data availability and quality
    if _has_fetch_errors(wallet_story):
        risk_score = FETCH_ERROR_SCORE
        evidence.append("Could not fetch transaction history; unable to assess.")
    elif _is_empty_wallet(wallet_story):
        risk_score = EMPTY_WALLET_SCORE
        evidence.append("New or empty wallet (no history) – higher baseline risk.")
    else:
        evidence.append("Transaction history retrieved successfully.")
        evidence.append(graph_summary)
        if _has_graph_proximity_risk(graph_summary):
            risk_score = GRAPH_PROXIMITY_SCORE

    # Generate appropriate summary based on risk level
    if risk_score >= HIGH_RISK_THRESHOLD:
        summary = "Higher risk indicators present. Review evidence and set OPENAI_API_KEY for full analysis."
    else:
        summary = (
            "Placeholder report (LLM not connected). "
            "Set OPENAI_API_KEY to synthesize risk from wallet story and RAG."
        )
        
    return (min(risk_score, 100), summary, evidence)


def _has_fetch_errors(wallet_story: str) -> bool:
    """Check if wallet story indicates data fetching errors."""
    return "Error fetching" in wallet_story


def _is_empty_wallet(wallet_story: str) -> bool:
    """Check if wallet appears to be new/empty with no transaction history."""
    return "No transactions found" in wallet_story


def _has_graph_proximity_risk(graph_summary: str) -> bool:
    """Check if graph analysis indicates proximity to known bad actors."""
    return "Graph: wallet is within" in graph_summary and "0" not in graph_summary


@router.post("/investigate", response_model=InvestigateResponse)
async def investigate_wallet(
    req: WalletRequest, 
    request: Request,
    current_user: Annotated[User, Depends(RequireInvestigate)],
    rate_limit: bool = Depends(strict_rate_limit)
) -> InvestigateResponse:
    """
    Comprehensive wallet investigation workflow.
    
    Process:
    1. Validate wallet address format
    2. Fetch on-chain transaction data from Etherscan
    3. Ingest transactions into graph database
    4. Gather graph context (proximity to known bad actors)
    5. Retrieve relevant threat intel via RAG
    6. Synthesize risk assessment (LLM if available, otherwise heuristic)
    
    Args:
        req: Wallet investigation request containing address and chain ID
        request: FastAPI request object (for app state access)
        current_user: Authenticated user with investigate permissions
        rate_limit: Rate limiting enforcement
        
    Returns:
        Risk assessment with score, summary, and evidence
    """
    # 1. Validate and normalize wallet address
    address = _validate_wallet_address(req.address)
    
    # 2. Fetch on-chain transaction data
    wallet_story, transactions = _fetch_transaction_data(address, req.chain_id)
    
    # 3. Ingest transaction data into graph database
    _ingest_to_graph(request.app, address, req.chain_id, transactions)
    
    # 4. Gather contextual information
    graph_summary = get_graph_context(address, request.app)
    rag_chunks = _get_threat_intelligence(wallet_story, address, request.app)
    
    # 5. Synthesize risk assessment
    risk_score, summary, evidence = _assess_risk(
        address, wallet_story, graph_summary, rag_chunks
    )

    return InvestigateResponse(
        address=address,
        risk_score=min(risk_score, 100),
        summary=summary,
        evidence=evidence,
    )


def _validate_wallet_address(address: str) -> str:
    """Validate and normalize Ethereum wallet address format."""
    normalized_address = address.strip()
    
    if not normalized_address:
        raise HTTPException(status_code=400, detail="Wallet address is required")
    
    if not normalized_address.startswith("0x"):
        raise HTTPException(status_code=400, detail="Wallet address must start with '0x'")
        
    if len(normalized_address) != 42:
        raise HTTPException(status_code=400, detail="Wallet address must be exactly 42 characters (0x + 40 hex chars)")
        
    return normalized_address


def _fetch_transaction_data(address: str, chain_id: int) -> tuple[str, list]:
    """Fetch transaction history from Etherscan API."""
    fetcher = EtherscanFetcher()
    return fetcher.get_tx_list_ok(address, chain_id=chain_id)


def _ingest_to_graph(app, address: str, chain_id: int, transactions: list) -> None:
    """Ingest transaction data into Neo4j graph database."""
    ingest_wallet_transactions(app, address, chain_id, transactions)


def _get_threat_intelligence(wallet_story: str, address: str, app) -> list[str]:
    """Retrieve relevant threat intelligence using RAG."""
    # Use first 500 chars of wallet story as behavior summary for semantic search
    max_summary_length = 500
    behaviour_summary = wallet_story[:max_summary_length]
    if len(wallet_story) > max_summary_length:
        behaviour_summary += "..."
    
    # Fallback to address if no story available
    query = behaviour_summary or address
    return get_rag_context(query, app, top_k=5)


def _assess_risk(address: str, wallet_story: str, graph_summary: str, rag_chunks: list[str]) -> tuple[int, str, list[str]]:
    """Generate risk assessment using LLM or heuristic fallback."""
    # Try LLM synthesis first
    llm_result = synthesize_risk(address, wallet_story, graph_summary, rag_chunks)
    
    if llm_result is not None:
        return llm_result
    
    # Fallback to heuristic assessment
    return _heuristic_risk(wallet_story, graph_summary)
