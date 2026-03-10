from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import investigate
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to Neo4j when configured so routes can use app.state.neo4j_driver
    app.state.neo4j_driver = None
    if settings.neo4j_password:
        try:
            from neo4j import GraphDatabase

            app.state.neo4j_driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
        except Exception:
            pass
    yield
    # Shutdown
    if getattr(app.state, "neo4j_driver", None):
        app.state.neo4j_driver.close()
        app.state.neo4j_driver = None


app = FastAPI(
    title="Faro",
    description="Blockchain forensic RAG agent – wallet risk investigation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(investigate.router, prefix="/api", tags=["investigate"])


@app.get("/health")
def health():
    return {"status": "ok"}
