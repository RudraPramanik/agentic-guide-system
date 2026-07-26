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
    APP_VERSION: str = "1.0.0"
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
    NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    OSRM_BASE_URL: str = "https://router.project-osrm.org"

    # Auth / JWT
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"
    GOOGLE_AUTH_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL: str = "https://www.googleapis.com/oauth2/v3/userinfo"

    # Rate limiting (in-memory backend; Redis at P6 via REDIS_URL)
    RATE_LIMIT_DEFAULT_REQUESTS: int = 60
    RATE_LIMIT_DEFAULT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_PLANNER_REQUESTS: int = 10
    RATE_LIMIT_PLANNER_WINDOW_SECONDS: int = 60
    RATE_LIMIT_PLANNER_PATH: str = "/api/v1/planner/generate"
    RATE_LIMIT_DESTINATIONS_SEARCH_REQUESTS: int = 20
    RATE_LIMIT_DESTINATIONS_SEARCH_WINDOW_SECONDS: int = 60
    RATE_LIMIT_DESTINATIONS_SEARCH_PATH: str = "/api/v1/destinations/search"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton for process lifetime."""

    return Settings()
