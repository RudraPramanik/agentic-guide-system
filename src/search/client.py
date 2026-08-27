"""Async Qdrant client + fail-soft places collection ensure."""

from __future__ import annotations

import asyncio

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qmodels
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from src.config import get_settings

log = structlog.get_logger()

_client: AsyncQdrantClient | None = None
_qdrant_available: bool = False  # pessimistic until ensure_places_collection() succeeds


def places_collection() -> str:
    """
    Single accessor for ensure / upsert / search / count_indexed.
    Cutover to hybrid: set QDRANT_PLACES_COLLECTION=places_v2 (same as V2 name).
    """
    return get_settings().QDRANT_PLACES_COLLECTION


def collection_uses_hybrid_schema() -> bool:
    """True when the active collection is the named-vector V2 hybrid collection."""
    settings = get_settings()
    return places_collection() == settings.QDRANT_PLACES_COLLECTION_V2


def get_qdrant_client() -> AsyncQdrantClient:
    """Lazy singleton, same pattern as core/database/session.py's get_engine()."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )
    return _client


def is_qdrant_available() -> bool:
    """The ONLY sanctioned way for other modules to check Qdrant availability."""
    return _qdrant_available


def _set_qdrant_available(value: bool) -> None:
    global _qdrant_available
    _qdrant_available = value


@retry(
    stop=stop_after_attempt(2),  # literal matches QDRANT_OPERATION_MAX_RETRIES default
    wait=wait_fixed(1),
    retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
)
async def _ensure_collection_impl() -> None:
    settings = get_settings()
    client = get_qdrant_client()
    name = places_collection()
    exists = await asyncio.wait_for(
        client.collection_exists(name),
        timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
    )
    if exists:
        return
    if collection_uses_hybrid_schema():
        await asyncio.wait_for(
            client.create_collection(
                collection_name=name,
                vectors_config={
                    "dense": qmodels.VectorParams(
                        size=settings.PLACES_EMBEDDING_DIM,
                        distance=qmodels.Distance.COSINE,
                    ),
                },
                sparse_vectors_config={
                    "bm25": qmodels.SparseVectorParams(),
                },
            ),
            timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
        )
    else:
        await asyncio.wait_for(
            client.create_collection(
                collection_name=name,
                vectors_config=qmodels.VectorParams(
                    size=settings.PLACES_EMBEDDING_DIM,
                    distance=qmodels.Distance.COSINE,
                ),
            ),
            timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
        )


async def ensure_places_collection() -> None:
    """
    MUST be safe to call during FastAPI lifespan startup — never raises.
    On any connectivity/auth/misconfig error after retries: log warning,
    set is_qdrant_available() to False, do NOT raise.
    """
    try:
        await _ensure_collection_impl()
        _set_qdrant_available(True)
    except Exception as exc:
        log.warning("qdrant.ensure_collection_failed", error=str(exc))
        _set_qdrant_available(False)


async def close_qdrant_client() -> None:
    """Call from lifespan shutdown — mirrors dispose_engine()."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
