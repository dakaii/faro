"""
Neo4j client for GraphRAG: graph traversal (multi-hop from wallet to blacklisted/mixer)
and vector index for threat reports (ReportChunk nodes).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.config import settings
from app.core.logging import ServiceLogger

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = ServiceLogger("neo4j")

# Label and property for RAG chunks (SPEC §8)
RAG_CHUNK_LABEL = "ReportChunk"
RAG_EMBEDDING_PROP = "embedding"
RAG_TEXT_PROP = "text"


class Neo4jConnectionError(Exception):
    """Raised when Neo4j connection fails."""
    pass


class Neo4jQueryError(Exception):
    """Raised when Neo4j query execution fails."""
    pass


def get_driver(app: FastAPI | None = None):
    """
    Return Neo4j driver: use app.state.neo4j_driver when app is provided (set at startup),
    otherwise lazy-init if configured. Returns None if not configured.
    """
    if app and getattr(app.state, "neo4j_driver", None):
        logger.debug("using_app_state_neo4j_driver")
        return app.state.neo4j_driver
        
    if not settings.neo4j_password:
        logger.debug("neo4j_not_configured", reason="no password")
        return None
        
    try:
        from neo4j import GraphDatabase
        
        logger.info("creating_neo4j_driver", uri=settings.neo4j_uri, user=settings.neo4j_user)
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        
        # Test connection
        driver.verify_connectivity()
        logger.info("neo4j_driver_created_successfully")
        return driver
        
    except Exception as e:
        logger.error("neo4j_connection_failed", error=e, uri=settings.neo4j_uri)
        raise Neo4jConnectionError(f"Failed to connect to Neo4j: {str(e)}") from e


def get_graph_context(address: str, app: FastAPI | None = None, max_hops: int = 3) -> str:
    """
    Run Cypher to find paths from this wallet to Blacklisted/Mixer nodes.
    Returns a string summary for the LLM.
    """
    try:
        driver = get_driver(app)
        if not driver:
            logger.debug("graph_context_unavailable", address=address, reason="neo4j not configured")
            return "Graph context unavailable (Neo4j not configured)."

        logger.debug("querying_graph_context", address=address, max_hops=max_hops)
        
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
            
            logger.info(
                "graph_context_queried",
                address=address,
                bad_paths=bad_paths,
                max_hops=max_hops
            )

        if bad_paths and bad_paths > 0:
            result_msg = f"Graph: wallet is within {max_hops} hops of {bad_paths} known bad/mixer node(s)."
        else:
            result_msg = "Graph: no path to known blacklisted or mixer nodes within max hops."
            
        logger.info("graph_context_result", address=address, result=result_msg)
        return result_msg
        
    except Neo4jConnectionError as e:
        logger.error("graph_context_connection_failed", address=address, error=e)
        return "Graph context unavailable (Neo4j connection failed)."
        
    except Exception as e:
        logger.error("graph_context_query_failed", address=address, error=e)
        return "Graph context unavailable (Query execution failed)."


def ensure_rag_vector_index(driver: Any) -> bool:
    """
    Create the RAG vector index if it does not exist (Neo4j 5.13+).
    Idempotent; safe to call at startup or before first ingest.
    """
    logger.info("ensuring_rag_vector_index", index_name=settings.rag_vector_index_name)
    
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
        
        logger.info(
            "rag_vector_index_ensured_successfully", 
            index_name=settings.rag_vector_index_name,
            dimensions=settings.openai_embedding_dimensions
        )
        return True
        
    except Exception as e:
        logger.error(
            "rag_vector_index_creation_failed",
            error=e,
            index_name=settings.rag_vector_index_name,
            dimensions=settings.openai_embedding_dimensions
        )
        return False


def get_rag_context(query: str, app: FastAPI | None = None, top_k: int = 5) -> list[str]:
    """
    Query Neo4j vector index for threat report chunks similar to query.
    Returns list of text snippets for the LLM. Uses OpenAI to embed query when configured.
    """
    from app.services.embeddings import embed_text

    logger.debug("getting_rag_context", query_length=len(query), top_k=top_k)
    
    driver = get_driver(app)
    if not driver:
        logger.debug("rag_context_unavailable", reason="neo4j not configured")
        return []

    query_embedding = embed_text(query)
    if not query_embedding:
        logger.warning("rag_context_unavailable", reason="embedding generation failed", query=query[:100])
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
            
            context_chunks = [record["text"] for record in result if record.get("text")]
            
            logger.info(
                "rag_context_retrieved",
                query_length=len(query),
                chunks_found=len(context_chunks),
                top_k=top_k,
                index_name=settings.rag_vector_index_name
            )
            
            return context_chunks
            
    except Neo4jConnectionError as e:
        logger.error("rag_context_connection_failed", query=query[:100], error=e)
        return []
        
    except Exception as e:
        logger.error(
            "rag_context_query_failed",
            query=query[:100],
            error=e,
            index_name=settings.rag_vector_index_name,
            top_k=top_k
        )
        raise Neo4jQueryError(f"Failed to query RAG context: {str(e)}") from e
