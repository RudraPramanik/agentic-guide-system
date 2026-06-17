"""Wandr - centralized application settings for environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str

    # Database
    DATABASE_URL: str

    # Vector search
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    # Cache
    REDIS_URL: str = ""

    # LLM
    LLM_MODEL: str = "nvidia_nim/meta/llama-3.1-8b-instruct"
    LLM_API_KEY: str
    LLM_API_BASE: str = ""
    LLM_TIMEOUT_SECONDS: int = 20
    LLM_MAX_RETRIES: int = 4

    # Planner agent bounds
    PLANNER_MAX_TOOL_CALLS: int = 12
    PLANNER_MAX_REPLAN_ATTEMPTS: int = 2
    PLANNER_GENERATION_TIMEOUT_SECONDS: int = 45
    PLANNER_MIN_READINESS_SCORE: float = 0.3
    PLANNER_AGENT_PHASE_STUCK_LIMIT: int = 3

    # Observability
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""

    # Geo
    NOMINATIM_USER_AGENT: str
    OSRM_BASE_URL: str = "https://router.project-osrm.org"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton for process lifetime."""

    return Settings()
