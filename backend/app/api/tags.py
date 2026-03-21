"""
Tag wallets as Blacklisted or Mixer for graph-based risk (multi-hop to bad actors).
"""
from typing import Annotated
from fastapi import APIRouter, Request, HTTPException, Depends

from app.core.auth import User, RequireTag
from app.middleware.rate_limit import standard_rate_limit
from app.models.schemas import TagAddressRequest, TagAddressResponse
from app.services.graph_tags import ALLOWED_TAGS, tag_wallet

router = APIRouter()


@router.post("/tag-address", response_model=TagAddressResponse)
async def tag_address_endpoint(
    request: Request, 
    body: TagAddressRequest,
    current_user: Annotated[User, Depends(RequireTag)],
    rate_limit: bool = Depends(standard_rate_limit)
) -> TagAddressResponse:
    """
    Tag a wallet as Blacklisted or Mixer in Neo4j. Creates the Wallet node if missing.
    Enables graph context to report "N hops from known bad actor" when investigating.
    """
    address = body.address.strip()
    if not address.startswith("0x") or len(address) != 42:
        raise HTTPException(status_code=400, detail="Invalid wallet address (0x + 40 hex chars)")
    tag = body.tag.strip()
    if tag not in ALLOWED_TAGS:
        raise HTTPException(
            status_code=400,
            detail=f"tag must be one of: {', '.join(sorted(ALLOWED_TAGS))}",
        )

    ok = tag_wallet(request.app, address, tag)
    if not ok:
        raise HTTPException(
            status_code=503,
            detail="Neo4j unavailable or write failed",
        )
    return TagAddressResponse(tagged=True, address=address, tag=tag)
