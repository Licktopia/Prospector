"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/prospector"
    test_database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/prospector_test"

    # API Keys
    serpapi_key: str = ""
    anthropic_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
