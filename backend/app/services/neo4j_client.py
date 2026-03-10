"""
Neo4j client for GraphRAG: graph traversal (multi-hop from wallet to blacklisted/mixer)
and vector index for threat reports (ReportChunk nodes).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.config import settings

if TYPE_CHECKING:
    from fastapi import FastAPI

# Label and property for RAG chunks (SPEC §8)
RAG_CHUNK_LABEL = "ReportChunk"
RAG_EMBEDDING_PROP = "embedding"
RAG_TEXT_PROP = "text"


def get_driver(app: FastAPI | None = None):
    """
    Return Neo4j driver: use app.state.neo4j_driver when app is provided (set at startup),
    otherwise lazy-init if configured. Returns None if not configured.
    """
    if app and getattr(app.state, "neo4j_driver", None):
        return app.state.neo4j_driver
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


def get_graph_context(address: str, app: FastAPI | None = None, max_hops: int = 3) -> str:
    """
    (Sprint 4) Run Cypher to find paths from this wallet to Blacklisted/Mixer nodes.
    Returns a string summary for the LLM.
    """
    driver = get_driver(app)
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


def ensure_rag_vector_index(driver: Any) -> bool:
    """
    Create the RAG vector index if it does not exist (Neo4j 5.13+).
    Idempotent; safe to call at startup or before first ingest.
    """
    try:
        with driver.session() as session:
            session.run(
                f"""
                CREATE VECTOR INDEX {settings.rag_vector_index_name} IF NOT EXISTS
                FOR (n:{RAG_CHUNK_LABEL}) ON (n.{RAG_EMBEDDING_PROP})
                OPTIONS {{
                    indexConfig: {{
                        `vector.dimensions`: $dimensions,
                        `vector.similarity_function`: 'cosine'
                    }}
                }}
                """,
                dimensions=settings.openai_embedding_dimensions,
            ).consume()
        return True
    except Exception:
        return False


def get_rag_context(query: str, app: FastAPI | None = None, top_k: int = 5) -> list[str]:
    """
    Query Neo4j vector index for threat report chunks similar to query.
    Returns list of text snippets for the LLM. Uses OpenAI to embed query when configured.
    """
    from app.services.embeddings import embed_text

    driver = get_driver(app)
    if not driver:
        return []

    query_embedding = embed_text(query)
    if not query_embedding:
        return []

    try:
        with driver.session() as session:
            result = session.run(
                f"""
                CALL db.index.vector.queryNodes($index_name, $top_k, $query_vector)
                YIELD node, score
                RETURN node.{RAG_TEXT_PROP} AS text
                """,
                index_name=settings.rag_vector_index_name,
                top_k=top_k,
                query_vector=query_embedding,
            )
            return [record["text"] for record in result if record.get("text")]
    except Exception:
        return []
