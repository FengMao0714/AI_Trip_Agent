"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    """Runtime settings for the Trip Planner backend."""

    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        alias="DEEPSEEK_BASE_URL",
    )
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="trip_planner", alias="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    amap_api_key: str = Field(default="", alias="AMAP_API_KEY")
    enable_amap_mcp: bool = Field(
        default=False,
        alias="ENABLE_AMAP_MCP",
    )
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    demo_fallback_enabled: bool = Field(
        default=True,
        alias="DEMO_FALLBACK_ENABLED",
    )
    preload_embedding_model: bool = Field(
        default=False,
        alias="PRELOAD_EMBEDDING_MODEL",
    )
    llm_thinking_enabled: bool = Field(
        default=False,
        alias="LLM_THINKING_ENABLED",
    )
    intent_extraction_llm_enabled: bool = Field(
        default=True,
        alias="INTENT_EXTRACTION_LLM_ENABLED",
    )

    model_config = SettingsConfigDict(
        env_file=BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings for dependency injection."""
    return Settings()
