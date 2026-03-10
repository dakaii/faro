from pydantic import BaseModel, Field


class WalletRequest(BaseModel):
    address: str = Field(..., description="Ethereum-style wallet address (0x...)")
    chain_id: int = Field(1, description="Chain ID (1=Ethereum, 8453=Base, 42161=Arbitrum)")


class InvestigateResponse(BaseModel):
    address: str
    risk_score: int = Field(..., ge=0, le=100)
    summary: str
    evidence: list[str] = Field(default_factory=list)


class TagAddressRequest(BaseModel):
    address: str = Field(..., description="Ethereum-style wallet address (0x...)")
    tag: str = Field(..., description="Label to apply: Blacklisted or Mixer")


class TagAddressResponse(BaseModel):
    tagged: bool
    address: str
    tag: str
