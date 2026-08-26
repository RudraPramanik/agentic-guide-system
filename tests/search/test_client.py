"""P3/V5: Qdrant client availability + ensure hybrid vs legacy."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.search import client as client_mod
from src.search.client import ensure_places_collection, is_qdrant_available


def test_is_qdrant_available_reflects_live_state_across_modules() -> None:
    """Importing the function (not a bool) observes live flips from another module."""
    client_mod._set_qdrant_available(False)
    assert is_qdrant_available() is False

    # Simulate another module calling the same function after a flip
    from src.search import places_index as places_index_mod

    client_mod._set_qdrant_available(True)
    assert places_index_mod.is_qdrant_available() is True

    client_mod._set_qdrant_available(False)
    assert places_index_mod.is_qdrant_available() is False


@pytest.mark.asyncio
async def test_ensure_hybrid_collection_creates_named_vectors() -> None:
    mock_client = AsyncMock()
    mock_client.collection_exists = AsyncMock(return_value=False)
    mock_client.create_collection = AsyncMock()
    settings = SimpleNamespace(
        QDRANT_OPERATION_TIMEOUT_SECONDS=5.0,
        PLACES_EMBEDDING_DIM=384,
        QDRANT_PLACES_COLLECTION="places_v2",
        QDRANT_PLACES_COLLECTION_V2="places_v2",
    )
    with (
        patch("src.search.client.get_qdrant_client", return_value=mock_client),
        patch("src.search.client.get_settings", return_value=settings),
    ):
        await ensure_places_collection()
        assert is_qdrant_available() is True
        kwargs = mock_client.create_collection.await_args.kwargs
        assert "dense" in kwargs["vectors_config"]
        assert "bm25" in kwargs["sparse_vectors_config"]


@pytest.mark.asyncio
async def test_ensure_legacy_collection_unnamed_dense() -> None:
    mock_client = AsyncMock()
    mock_client.collection_exists = AsyncMock(return_value=False)
    mock_client.create_collection = AsyncMock()
    settings = SimpleNamespace(
        QDRANT_OPERATION_TIMEOUT_SECONDS=5.0,
        PLACES_EMBEDDING_DIM=384,
        QDRANT_PLACES_COLLECTION="places",
        QDRANT_PLACES_COLLECTION_V2="places_v2",
    )
    with (
        patch("src.search.client.get_qdrant_client", return_value=mock_client),
        patch("src.search.client.get_settings", return_value=settings),
    ):
        await ensure_places_collection()
        kwargs = mock_client.create_collection.await_args.kwargs
        assert not isinstance(kwargs["vectors_config"], dict)
        assert "sparse_vectors_config" not in kwargs


@pytest.mark.asyncio
async def test_ensure_fail_soft_on_qdrant_error() -> None:
    with patch(
        "src.search.client._ensure_collection_impl",
        new=AsyncMock(side_effect=ConnectionError("down")),
    ):
        await ensure_places_collection()
        assert is_qdrant_available() is False
