"""
Neo4j client for GraphRAG: graph traversal (multi-hop from wallet to blacklisted/mixer)
and vector index for threat reports. Placeholder until Sprint 2/4.
"""
from typing import Any

from app.core.config import settings


def get_driver():
    """Lazy init Neo4j driver. Returns None if not configured."""
    if not settings.neo4j_password:
        return None
    try:
        from neo4j import GraphDatabase

        return GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    except Exception:
        return None


def get_graph_context(address: str, max_hops: int = 3) -> str:
    """
    (Sprint 4) Run Cypher to find paths from this wallet to Blacklisted/Mixer nodes.
    Returns a string summary for the LLM.
    """
    driver = get_driver()
    if not driver:
        return "Graph context unavailable (Neo4j not configured)."

    # Placeholder Cypher – to be implemented in Sprint 4
    # e.g. MATCH path = (w:Wallet {address: $address})-[:SENT_FUNDS*1..3]-(bad) WHERE bad:Blacklisted OR bad:Mixer RETURN path
    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (w:Wallet {address: $address})
                OPTIONAL MATCH path = (w)-[:SENT_FUNDS*1..3]-(other)
                WHERE other:Blacklisted OR other:Mixer
                RETURN count(path) AS bad_paths
                """,
                address=address,
            )
            record = result.single()
            bad_paths = (record and record.get("bad_paths")) or 0
    except Exception:
        return "Graph context unavailable (Neo4j schema not initialized)."

    if bad_paths and bad_paths > 0:
        return f"Graph: wallet is within {max_hops} hops of {bad_paths} known bad/mixer node(s)."
    return "Graph: no path to known blacklisted or mixer nodes within max hops."


def get_rag_context(query: str, top_k: int = 5) -> list[str]:
    """
    (Sprint 2) Query Neo4j vector index for threat report chunks similar to query.
    Returns list of text snippets for the LLM.
    """
    driver = get_driver()
    if not driver:
        return []

    # Placeholder – vector index and Cypher will be added in Sprint 2
    return []
