"""
Tag wallets as Blacklisted or Mixer in Neo4j so graph traversal can find paths to bad actors.
"""
from typing import Any

from app.services.neo4j_client import get_driver

ALLOWED_TAGS = frozenset({"Blacklisted", "Mixer"})


def tag_wallet(app: Any, address: str, tag: str) -> bool:
    """
    MERGE Wallet node and add label Blacklisted or Mixer. Idempotent.
    Returns True if the write succeeded, False if driver unavailable or invalid tag.
    """
    address = (address or "").strip()
    if not address.startswith("0x") or len(address) != 42:
        return False
    if tag not in ALLOWED_TAGS:
        return False

    driver = get_driver(app) if app else get_driver()
    if not driver:
        return False

    try:
        with driver.session() as session:
            # MERGE Wallet, add label (Cypher doesn't allow parameterized labels, so branch)
            if tag == "Blacklisted":
                session.run(
                    "MERGE (w:Wallet {address: $address}) SET w:Blacklisted RETURN w",
                    address=address,
                ).consume()
            else:
                session.run(
                    "MERGE (w:Wallet {address: $address}) SET w:Mixer RETURN w",
                    address=address,
                ).consume()
        return True
    except Exception:
        return False
