"""Application configuration loaded only from local environment variables."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Secrets must never be logged or returned by the API."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    euri_api_base_url: str = "https://api.euron.one/api/v1/euri"
    euri_api_key: SecretStr | None = None
    euri_llm_model: str = "gpt-5.3-instant"
    euri_embedding_model: str = "gemini-embedding-2"
    euri_embedding_base_url: str = "https://api.euron.one/api/v1/euri/embeddings"
    euri_embedding_dimension: int = Field(default=3072, gt=0)

    qdrant_url: str | None = None
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "sentinel_policy_chunks"

    neo4j_uri: str | None = None
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr | None = None
    neo4j_database: str = "neo4j"

    supabase_url: str | None = None
    supabase_key: SecretStr | None = None

    euri_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    euri_max_retries: int = Field(default=2, ge=0, le=5)


@lru_cache
def get_settings() -> Settings:
    return Settings()
