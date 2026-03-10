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


settings = Settings()
