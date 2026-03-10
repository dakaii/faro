"""
Ingest Etherscan transaction data into Neo4j: Wallet nodes and SENT_FUNDS relationships.
Uses execute_write and batched MERGE for idempotent, ACID-safe writes.
"""
from typing import Any

from app.services.neo4j_client import get_driver


def _normalize_tx_for_ingest(tx: dict[str, Any], chain_id: int) -> dict[str, Any] | None:
    """Extract and normalize fields for one tx. Returns None if invalid."""
    from_addr = (tx.get("from") or "").strip()
    if not from_addr or not from_addr.startswith("0x"):
        return None
    to_addr = (tx.get("to") or "").strip() or "0x0"  # contract creation → sentinel
    if not to_addr.startswith("0x"):
        to_addr = "0x0"
    tx_hash = (tx.get("hash") or "").strip()
    if not tx_hash:
        return None
    try:
        value_wei = int(tx.get("value", 0))
        timestamp = int(tx.get("timeStamp", 0))
    except (TypeError, ValueError):
        value_wei = 0
        timestamp = 0
    return {
        "from_address": from_addr,
        "to_address": to_addr,
        "tx_hash": tx_hash,
        "value_wei": value_wei,
        "timestamp": timestamp,
        "chain_id": chain_id,
    }


def ingest_wallet_transactions(
    app: Any,
    address: str,
    chain_id: int,
    txs: list[dict[str, Any]],
    *,
    batch_size: int = 50,
) -> int:
    """
    Write Wallet nodes and SENT_FUNDS edges from Etherscan tx list into Neo4j.
    Uses MERGE so repeated calls are idempotent. Returns number of relationships written.
    Best practice: use execute_write and batch with UNWIND.
    """
    driver = get_driver(app) if app else get_driver()
    if not driver:
        return 0

    rows = []
    for tx in txs:
        row = _normalize_tx_for_ingest(tx, chain_id)
        if row:
            rows.append(row)
    if not rows:
        return 0

    def _write(tx: Any) -> int:
        # Process in batches to avoid huge single transaction
        total = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            tx.run(
                """
                UNWIND $batch AS row
                MERGE (a:Wallet {address: row.from_address})
                MERGE (b:Wallet {address: row.to_address})
                MERGE (a)-[r:SENT_FUNDS {tx_hash: row.tx_hash}]->(b)
                ON CREATE SET
                    r.amount_wei = row.value_wei,
                    r.timestamp = row.timestamp,
                    r.chain_id = row.chain_id
                RETURN count(r) AS n
                """,
                batch=batch,
            ).consume()
            total += len(batch)
        return total

    try:
        with driver.session() as session:
            return session.execute_write(_write)
    except Exception:
        return 0
