"""
Integration tests that run real Cypher against Neo4j.
Run only when Neo4j is available: `make up` then `make test` (or pytest -m neo4j).
Otherwise these tests are skipped.
"""
import pytest

from app.services.graph_tags import tag_wallet
from app.services.neo4j_client import get_graph_context

# Unique addresses so we don't clash with real data; cleanup after
ADDR_BAD = "0x0000000000000000000000000000000000000001"
ADDR_SENDER = "0x0000000000000000000000000000000000000002"


@pytest.mark.neo4j
def test_tag_wallet_and_graph_context_path(neo4j_driver):
    """
    Tag a wallet as Blacklisted, create a sender with SENT_FUNDS to it,
    then get_graph_context(sender) must find the path to the bad actor.
    """
    # 1. Tag the "bad" wallet so graph traversal can find it
    ok = tag_wallet(None, ADDR_BAD, "Blacklisted")
    assert ok, "tag_wallet should succeed when Neo4j is available"

    # 2. Create sender wallet and one SENT_FUNDS edge to the blacklisted wallet
    with neo4j_driver.session() as session:
        session.run(
            """
            MERGE (a:Wallet {address: $from_addr})
            MERGE (b:Wallet {address: $to_addr})
            MERGE (a)-[r:SENT_FUNDS {tx_hash: $tx_hash}]->(b)
            SET r.amount_wei = 0, r.timestamp = 0, r.chain_id = 1
            """,
            from_addr=ADDR_SENDER,
            to_addr=ADDR_BAD,
            tx_hash="0xintegration_test_tx",
        ).consume()

    try:
        # 3. Graph context for the sender should report path to Blacklisted
        result = get_graph_context(ADDR_SENDER, app=None)
        assert "Graph context unavailable" not in result or "bad" in result.lower()
        assert "within" in result and "hop" in result.lower()
        assert "1" in result  # one path / one hop
    finally:
        # 4. Cleanup: remove test nodes and relationships
        with neo4j_driver.session() as session:
            session.run(
                "MATCH (w:Wallet) WHERE w.address IN $addrs DETACH DELETE w",
                addrs=[ADDR_BAD, ADDR_SENDER],
            ).consume()


@pytest.mark.neo4j
def test_graph_context_no_path_without_bad_node(neo4j_driver):
    """
    A wallet with no path to Blacklisted/Mixer should get "no path" message.
    We use an address we never tag or link to a bad actor.
    """
    orphan = "0x0000000000000000000000000000000000000003"
    with neo4j_driver.session() as session:
        session.run("MERGE (w:Wallet {address: $address})", address=orphan).consume()
    try:
        result = get_graph_context(orphan, app=None)
        assert "no path" in result.lower() or "0" in result
    finally:
        with neo4j_driver.session() as session:
            session.run("MATCH (w:Wallet {address: $a}) DETACH DELETE w", a=orphan).consume()
