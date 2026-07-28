"""Embedding abstraction — lifespan-loaded, thread-offloaded, fail-soft."""

from __future__ import annotations

import asyncio

import structlog
from sentence_transformers import SentenceTransformer

from src.config import get_settings

log = structlog.get_logger()

_model: SentenceTransformer | None = None
_embeddings_available: bool = False


def is_embeddings_available() -> bool:
    """The ONLY sanctioned way for other modules to check embedding availability."""
    return _embeddings_available


async def ensure_embedding_model_loaded() -> None:
    """
    Call once from lifespan startup, alongside ensure_places_collection().
    Never raises. Do NOT retry inside this function (a failed load is a permanent-until-
    restart condition — env/network/disk issue, not transient).
    """
    global _model, _embeddings_available
    settings = get_settings()
    try:
        _model = await asyncio.wait_for(
            asyncio.to_thread(SentenceTransformer, settings.PLACES_EMBEDDING_MODEL),
            timeout=settings.PLACES_EMBEDDING_MODEL_LOAD_TIMEOUT_SECONDS,
        )
        _embeddings_available = True
    except Exception as exc:
        log.warning("embeddings.model_load_failed", error=str(exc))
        _model = None
        _embeddings_available = False


async def embed_text(text: str) -> list[float]:
    """Returns [] if embeddings unavailable or text is blank. Never raises."""
    if not _embeddings_available or not text.strip():
        return []
    vector = await asyncio.to_thread(_model.encode, text)
    return vector.tolist()


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    LOCKED (v2): parallel-array contract — one output per input, in order.
    Unavailable -> [[] for _ in texts], never a bare [].
    """
    if not _embeddings_available:
        return [[] for _ in texts]
    vectors = await asyncio.to_thread(_model.encode, texts)
    return [v.tolist() for v in vectors]
