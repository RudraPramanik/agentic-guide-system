"""P3: embeddings fail-soft + parallel-array batch contract."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

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

    embed_task = asyncio.create_task(embeddings_mod.embed_text("x"))
    other_task = asyncio.create_task(concurrent())
    results = await asyncio.gather(embed_task, other_task)

    assert len(results[0]) == 384
    assert results[1] == "ok"
    assert progress == ["tick"]
    assert finished.is_set()

    embeddings_mod._model = None
    embeddings_mod._embeddings_available = False
