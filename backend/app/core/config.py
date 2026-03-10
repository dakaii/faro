from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Faro"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Etherscan V2 – https://etherscan.io/apis
    etherscan_api_key: str = ""
    etherscan_base_url: str = "https://api.etherscan.io/v2/api"

    # Neo4j – bolt://localhost:7687 for local
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
