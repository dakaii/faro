import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api import auth, investigate, ingest, tags
from app.core.config import settings
from app.core.logging import configure_logging, get_logger, LoggingMiddleware
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler

# Configure logging on module import
configure_logging()
logger = get_logger("startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate production settings on startup
    if os.getenv("ENVIRONMENT") == "production":
        try:
            settings.validate_production_settings()
            logger.info("production_config_validated")
        except ValueError as e:
            logger.error("production_config_invalid", error=str(e))
            raise
    
    # Startup: connect to Neo4j when configured
    app.state.neo4j_driver = None
    if settings.neo4j_password:
        try:
            from neo4j import GraphDatabase
            
            logger.info("connecting_to_neo4j", uri=settings.neo4j_uri, user=settings.neo4j_user)
            app.state.neo4j_driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            logger.info("neo4j_connected")
            
            # Ensure RAG vector index exists when Neo4j + OpenAI are configured
            if settings.openai_api_key or settings.openai_base_url:
                from app.services.neo4j_client import ensure_rag_vector_index
                logger.info("ensuring_rag_vector_index")
                ensure_rag_vector_index(app.state.neo4j_driver)
                logger.info("rag_vector_index_ready")
        except Exception as e:
            logger.error("neo4j_connection_failed", error=str(e))
            # Don't fail startup - Neo4j is optional
    else:
        logger.info("neo4j_disabled", reason="no password configured")
    
    logger.info("application_startup_complete")
    yield
    
    # Shutdown
    if getattr(app.state, "neo4j_driver", None):
        logger.info("closing_neo4j_connection")
        app.state.neo4j_driver.close()
        app.state.neo4j_driver = None
        logger.info("neo4j_connection_closed")


app = FastAPI(
    title="Faro",
    description="Blockchain forensic RAG agent – wallet risk investigation",
    version="0.1.0",
    lifespan=lifespan,
)

# Add rate limiting state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add logging middleware first (runs last)
app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(investigate.router, prefix="/api", tags=["investigate"])
app.include_router(ingest.router, prefix="/api", tags=["ingest"])
app.include_router(tags.router, prefix="/api", tags=["tags"])


@app.get("/health")
def health():
    return {"status": "ok"}
