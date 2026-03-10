"""
Test data builders (no ORM – we don't use Postgres).
Use these instead of inline dicts so "what does an Etherscan tx look like" lives in one place.
Override only the fields you care about in each test.
"""

# Valid 0x + 40 hex
DEFAULT_FROM = "0xfrom1234567890123456789012345678901234567890"
DEFAULT_TO = "0xto1234567890123456789012345678901234567890"
DEFAULT_ADDRESS = "0x1234567890123456789012345678901234567890"


def tx_etherscan(
    *,
    from_addr: str = DEFAULT_FROM,
    to_addr: str = DEFAULT_TO,
    tx_hash: str = "0xhash123",
    value: str = "1000000000000000000",
    time_stamp: str = "1704067200",
    **overrides: str,
) -> dict:
    """Build an Etherscan-style tx dict (account txlist). Override any field via kwargs."""
    d = {
        "from": from_addr,
        "to": to_addr,
        "hash": tx_hash,
        "value": value,
        "timeStamp": time_stamp,
    }
    d.update(overrides)
    return d


def investigate_request(
    *,
    address: str = DEFAULT_ADDRESS,
    chain_id: int = 1,
) -> dict:
    """Build POST /api/investigate request body."""
    return {"address": address, "chain_id": chain_id}


def tag_request(
    *,
    address: str = DEFAULT_ADDRESS,
    tag: str = "Blacklisted",
) -> dict:
    """Build POST /api/tag-address request body."""
    return {"address": address, "tag": tag}
