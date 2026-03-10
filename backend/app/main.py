from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import investigate
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init Neo4j driver etc. later
    yield
    # Shutdown
    if hasattr(app.state, "neo4j_driver") and app.state.neo4j_driver:
        app.state.neo4j_driver.close()


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
