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

    # Vector search (host port 6335 — compose maps 6335:6333)
    QDRANT_URL: str = "http://localhost:6335"
    QDRANT_API_KEY: str = ""
    QDRANT_PLACES_COLLECTION: str = "places"
    # local = MiniLM in-process (dev); hosted = LiteLLM embedding API (prod)
    PLACES_EMBEDDING_BACKEND: str = "local"
    # Dim must match backend model + Qdrant collection (MiniLM 384; gemini/text-embedding-004 → 768)
    PLACES_EMBEDDING_DIM: int = 384
    QDRANT_OPERATION_TIMEOUT_SECONDS: float = 5.0
    QDRANT_OPERATION_MAX_RETRIES: int = 2
    PLACES_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    # First download of MiniLM often exceeds 30s on cold cache — allow headroom locally.
    PLACES_EMBEDDING_MODEL_LOAD_TIMEOUT_SECONDS: float = 120.0
    ENRICH_BATCH_LLM_CONCURRENCY: int = 3
    # Gemini / Google AI key for LiteLLM gemini/* embeddings (and optional Gemini chat)
    GEMINI_API_KEY: str = ""

    # Cache / Redis backends (empty REDIS_URL → in-memory rate limit + planner cache)
    REDIS_URL: str = ""
    REDIS_CONNECT_TIMEOUT_SECONDS: float = 1.0
    REDIS_SOCKET_TIMEOUT_SECONDS: float = 1.0

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
    # Absolute floor before graph/cache (HTTP 409); soft readiness stays in-graph
    PLANNER_ABSOLUTE_MIN_PLACES: int = 10
    # Planner result cache TTL — used from P6.4; declared now
    PLANNER_CACHE_TTL_SECONDS: int = 3600

    # Observability
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""

    # Geo
    NOMINATIM_USER_AGENT: str
    NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    OSRM_BASE_URL: str = "https://router.project-osrm.org"
    # Bounded parallelism for OsrmRoutingProvider.travel_matrix (public OSRM-safe)
    OSRM_MATRIX_MAX_CONCURRENCY: int = 8
    # Generate + trip-edit routing adapter: haversine = in-process (default, fits 45s);
    # osrm = live pairwise get_route against OSRM_BASE_URL (paid/self-host later).
    ROUTING_BACKEND: str = "haversine"

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
    # User-keyed trip edit dependency (not path-table); middleware IP default may still apply
    RATE_LIMIT_TRIP_EDIT_REQUESTS: int = 20
    RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS: int = 60
    # IP-keyed destination prepare (UUID path — not in _route_limit_table)
    RATE_LIMIT_DESTINATIONS_PREPARE_REQUESTS: int = 5
    RATE_LIMIT_DESTINATIONS_PREPARE_WINDOW_SECONDS: int = 60
    # In-flight prepare lock TTL so a dead worker cannot pin "preparing" forever
    DESTINATIONS_PREPARE_LOCK_TTL_SECONDS: int = 180
    DESTINATIONS_PREPARE_DEFAULT_RADIUS_KM: float = 30.0
    DESTINATIONS_PREPARE_MAX_RADIUS_KM: float = 50.0

    # CORS (credentialed; explicit origins only — never "*" with credentials)
    CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton for process lifetime."""

    return Settings()
