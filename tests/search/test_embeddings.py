"""P3: embeddings fail-soft + parallel-array batch + hosted backend."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.search import embeddings as embeddings_mod


@pytest.mark.asyncio
async def test_embed_text_returns_empty_when_unavailable() -> None:
    embeddings_mod._model = None
    embeddings_mod._embeddings_available = False
    assert await embeddings_mod.embed_text("x") == []


@pytest.mark.asyncio
async def test_embed_batch_parallel_empty_when_unavailable() -> None:
    embeddings_mod._model = None
    embeddings_mod._embeddings_available = False
    assert await embeddings_mod.embed_batch(["a", "b"]) == [[], []]


@pytest.mark.asyncio
async def test_embed_text_returns_384_when_model_mocked() -> None:
    mock_model = MagicMock()
    mock_model.encode = MagicMock(return_value=np.zeros(384))
    embeddings_mod._model = mock_model
    embeddings_mod._embeddings_available = True
    with patch("src.search.embeddings.get_settings") as gs:
        gs.return_value = MagicMock(PLACES_EMBEDDING_BACKEND="local")
        vector = await embeddings_mod.embed_text("sunrise photography")
    assert isinstance(vector, list) and len(vector) == 384
    embeddings_mod._model = None
    embeddings_mod._embeddings_available = False


@pytest.mark.asyncio
async def test_embed_text_does_not_block_event_loop() -> None:
    """encode sleeps in a thread; a concurrent coroutine must still make progress."""
    started = asyncio.Event()
    finished = asyncio.Event()

    def slow_encode(_text):
        started.set()
        import time

        time.sleep(0.2)
        finished.set()
        return np.zeros(384)

    mock_model = MagicMock()
    mock_model.encode = slow_encode
    embeddings_mod._model = mock_model
    embeddings_mod._embeddings_available = True

    progress = []

    async def concurrent():
        await started.wait()
        progress.append("tick")
        return "ok"

    with patch("src.search.embeddings.get_settings") as gs:
        gs.return_value = MagicMock(PLACES_EMBEDDING_BACKEND="local")
        embed_task = asyncio.create_task(embeddings_mod.embed_text("x"))
        other_task = asyncio.create_task(concurrent())
        results = await asyncio.gather(embed_task, other_task)

    assert len(results[0]) == 384
    assert results[1] == "ok"
    assert progress == ["tick"]
    assert finished.is_set()

    embeddings_mod._model = None
    embeddings_mod._embeddings_available = False


@pytest.mark.asyncio
async def test_hosted_embed_text_uses_gateway_dim() -> None:
    embeddings_mod._model = None
    embeddings_mod._embeddings_available = True
    fake = AsyncMock(return_value=[[0.1] * 768])
    with (
        patch("src.search.embeddings.get_settings") as gs,
        patch("src.core.llm.client.embed_texts", new=fake),
    ):
        gs.return_value = MagicMock(PLACES_EMBEDDING_BACKEND="hosted")
        vector = await embeddings_mod.embed_text("quiet cafes")
    assert len(vector) == 768
    fake.assert_awaited_once()
    embeddings_mod._embeddings_available = False


@pytest.mark.asyncio
async def test_hosted_embed_batch_fail_soft_shape() -> None:
    embeddings_mod._embeddings_available = True
    with (
        patch("src.search.embeddings.get_settings") as gs,
        patch(
            "src.core.llm.client.embed_texts",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
    ):
        gs.return_value = MagicMock(PLACES_EMBEDDING_BACKEND="hosted")
        assert await embeddings_mod.embed_batch(["a", "b"]) == [[], []]
    embeddings_mod._embeddings_available = False


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="optional live Gemini embed — set GEMINI_API_KEY to run",
)
async def test_live_gemini_embed_optional() -> None:
    """Live smoke; skipped unless GEMINI_API_KEY is set in the environment."""
    from src.core.llm.client import embed_texts

    vectors = await embed_texts(["wandr live embed smoke"])
    assert len(vectors) == 1
    assert len(vectors[0]) >= 64


@pytest.mark.asyncio
async def test_hosted_ensure_skips_sentence_transformer() -> None:
    embeddings_mod._model = object()
    embeddings_mod._embeddings_available = False
    settings = MagicMock(
        PLACES_EMBEDDING_BACKEND="hosted",
        GEMINI_API_KEY="g-key",
        LLM_API_KEY="",
        PLACES_EMBEDDING_MODEL="gemini/text-embedding-004",
        PLACES_EMBEDDING_DIM=768,
    )
    with (
        patch("src.search.embeddings.get_settings", return_value=settings),
        patch.dict("sys.modules", {"sentence_transformers": None}),
    ):
        await embeddings_mod.ensure_embedding_model_loaded()
    assert embeddings_mod._embeddings_available is True
    assert embeddings_mod._model is None
