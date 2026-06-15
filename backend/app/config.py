"""Application configuration, loaded from environment / .env.

Every provider credential is optional. With nothing set, the app runs on the
built-in `stub` provider and an in-memory SQLite database, so a fresh clone
boots with zero external dependencies.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Backing services. SQLite default keeps the app runnable without Docker.
    database_url: str = "sqlite+pysqlite:///./ads.db"
    qdrant_url: str = "http://localhost:6333"
    # When Qdrant is unreachable the RAG layer falls back to a local on-disk
    # vector store rooted here, so retrieval works with zero external services.
    local_vector_path: str = "./vector_data"
    # How long to wait when probing/using Qdrant before falling back (seconds).
    qdrant_timeout: float = 2.0

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "ads-password"

    # Default model selection, "<provider>:<model>".
    default_chat_model: str = "stub:echo"
    default_embed_model: str = "stub:echo-embed"

    # Provider credentials / endpoints (all optional).
    ollama_base_url: str = "http://localhost:11434"

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    nim_api_key: str | None = None
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"

    anthropic_api_key: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com"

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
