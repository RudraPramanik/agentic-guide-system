"""Embedding abstraction — lifespan-init, fail-soft; local MiniLM or hosted LiteLLM."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from src.config import get_settings

log = structlog.get_logger()

_model: Any | None = None
_embeddings_available: bool = False


def is_embeddings_available() -> bool:
    """The ONLY sanctioned way for other modules to check embedding availability."""
    return _embeddings_available


async def ensure_embedding_model_loaded() -> None:
    """
    Call once from lifespan startup, alongside ensure_places_collection().
    Never raises. Hosted: no SentenceTransformer. Local: load MiniLM once.
    """
    global _model, _embeddings_available
    settings = get_settings()
    backend = (settings.PLACES_EMBEDDING_BACKEND or "local").strip().lower()

    if backend == "hosted":
        _model = None
        try:
            key = settings.GEMINI_API_KEY or settings.LLM_API_KEY
            if not key or not settings.PLACES_EMBEDDING_MODEL:
                raise ValueError("hosted embeddings missing API key or model")
            _embeddings_available = True
            log.info(
                "embeddings.hosted_ready",
                model=settings.PLACES_EMBEDDING_MODEL,
                dim=settings.PLACES_EMBEDDING_DIM,
            )
        except Exception as exc:
            log.warning("embeddings.hosted_init_failed", error=str(exc))
            _embeddings_available = False
        return

    # local MiniLM — lazy import so prod images without sentence-transformers can boot hosted
    try:
        from sentence_transformers import SentenceTransformer

        _model = await asyncio.wait_for(
            asyncio.to_thread(SentenceTransformer, settings.PLACES_EMBEDDING_MODEL),
            timeout=settings.PLACES_EMBEDDING_MODEL_LOAD_TIMEOUT_SECONDS,
        )
        _embeddings_available = True
    except Exception as exc:
        log.warning("embeddings.model_load_failed", error=str(exc))
        _model = None
        _embeddings_available = False


async def _embed_hosted(texts: list[str]) -> list[list[float]]:
    from src.core.llm.client import embed_texts

    try:
        return await embed_texts(texts)
    except Exception as exc:
        log.warning("embeddings.hosted_failed", error=str(exc), n=len(texts))
        return [[] for _ in texts]


async def embed_text(text: str) -> list[float]:
    """Returns [] if embeddings unavailable or text is blank. Never raises."""
    if not _embeddings_available or not text.strip():
        return []
    settings = get_settings()
    backend = (settings.PLACES_EMBEDDING_BACKEND or "local").strip().lower()
    if backend == "hosted":
        vectors = await _embed_hosted([text])
        return vectors[0] if vectors else []
    if _model is None:
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
    if not texts:
        return []
    settings = get_settings()
    backend = (settings.PLACES_EMBEDDING_BACKEND or "local").strip().lower()
    if backend == "hosted":
        return await _embed_hosted(texts)
    if _model is None:
        return [[] for _ in texts]
    vectors = await asyncio.to_thread(_model.encode, texts)
    return [v.tolist() for v in vectors]
