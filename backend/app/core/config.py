from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Faro"
    # Override via env: CORS_ORIGINS="https://app.example.com,https://admin.example.com"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str] | None) -> list[str]:
        if v is None:
            return ["http://localhost:5173", "http://localhost:3000"]
        if isinstance(v, list):
            return v
        if isinstance(v, str) and v.strip():
            return [o.strip() for o in v.split(",") if o.strip()]
        return ["http://localhost:5173", "http://localhost:3000"]

    # Etherscan V2 – https://etherscan.io/apis
    etherscan_api_key: str = ""
    etherscan_base_url: str = "https://api.etherscan.io/v2/api"

    # Neo4j – bolt://localhost:7687 for local
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    # LLM & embeddings – OpenAI-compatible (OpenAI, OpenRouter, self-hosted). Optional (heuristic when unset).
    # When base_url is set, use that endpoint for both; api_key can be OpenAI key, OpenRouter key, or any key the server accepts.
    openai_api_key: str = ""
    openai_base_url: str = ""  # e.g. https://openrouter.ai/api/v1 or http://localhost:11434/v1 (Ollama)
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536  # some providers ignore this (fixed-dim models)
    openai_llm_model: str = "gpt-4o-mini"

    # RAG – Neo4j vector index for ReportChunk nodes
    rag_vector_index_name: str = "report_chunks_vector"


settings = Settings()
