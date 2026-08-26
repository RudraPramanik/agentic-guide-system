"""P3: places_index upsert / search / count contracts (mocked Qdrant)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from qdrant_client import models as qmodels

from src.search.places_index import (
    count_indexed,
    search_places,
    upsert_place,
    upsert_places_batch,
)


@pytest.mark.asyncio
async def test_upsert_place_false_when_embedding_empty() -> None:
    place = SimpleNamespace(
        id=uuid.uuid4(),
        summary="S",
        enriched_tags=[],
        name="N",
        osm_id="1",
        category="viewpoint",
    )
    with patch(
        "src.search.places_index.embed_text", new=AsyncMock(return_value=[])
    ):
        assert await upsert_place(place, uuid.uuid4()) is False


@pytest.mark.asyncio
async def test_upsert_place_uses_deterministic_point_id() -> None:
    place_id = uuid.uuid4()
    place = SimpleNamespace(
        id=place_id,
        summary="S",
        enriched_tags=["photography"],
        name="N",
        osm_id="1",
        category="viewpoint",
    )
    mock_client = AsyncMock()
    mock_client.upsert = AsyncMock()
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch(
            "src.search.places_index.embed_text",
            new=AsyncMock(return_value=[0.0] * 384),
        ),
    ):
        assert await upsert_place(place, uuid.uuid4()) is True
        points = mock_client.upsert.await_args.kwargs["points"]
        assert points[0].id == str(place_id)


@pytest.mark.asyncio
async def test_upsert_places_batch_single_qdrant_call() -> None:
    dest_id = uuid.uuid4()
    places = [
        SimpleNamespace(
            id=uuid.uuid4(),
            summary="S",
            enriched_tags=[],
            name="A",
            osm_id="1",
            category="viewpoint",
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            summary="S2",
            enriched_tags=[],
            name="B",
            osm_id="2",
            category="museum",
        ),
    ]
    mock_client = AsyncMock()
    mock_client.upsert = AsyncMock()
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch(
            "src.search.places_index.embed_batch",
            new=AsyncMock(return_value=[[0.0] * 384, [0.0] * 384]),
        ),
    ):
        assert await upsert_places_batch(places, dest_id) == 2
        assert mock_client.upsert.await_count == 1


@pytest.mark.asyncio
async def test_search_places_returns_empty_on_qdrant_error() -> None:
    mock_client = AsyncMock()
    mock_client.query_points = AsyncMock(side_effect=RuntimeError("down"))
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch(
            "src.search.places_index.embed_text",
            new=AsyncMock(return_value=[0.0] * 384),
        ),
        patch("src.search.places_index.is_qdrant_available", return_value=True),
    ):
        assert await search_places("q", uuid.uuid4()) == []


@pytest.mark.asyncio
async def test_search_places_short_circuits_on_empty_embedding() -> None:
    mock_client = AsyncMock()
    mock_client.query_points = AsyncMock()
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch("src.search.places_index.embed_text", new=AsyncMock(return_value=[])),
        patch("src.search.places_index.is_qdrant_available", return_value=True),
    ):
        assert await search_places("q", uuid.uuid4()) == []
        assert mock_client.query_points.await_count == 0


@pytest.mark.asyncio
async def test_search_places_includes_destination_filter() -> None:
    dest_id = uuid.uuid4()
    mock_client = AsyncMock()
    mock_client.query_points = AsyncMock(
        return_value=SimpleNamespace(points=[])
    )
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch(
            "src.search.places_index.embed_text",
            new=AsyncMock(return_value=[0.0] * 384),
        ),
        patch("src.search.places_index.is_qdrant_available", return_value=True),
    ):
        await search_places("q", dest_id, top_k=5)
        kwargs = mock_client.query_points.await_args.kwargs
        filt: qmodels.Filter = kwargs["query_filter"]
        assert filt.must[0].match.value == str(dest_id)


@pytest.mark.asyncio
async def test_count_indexed_uses_qdrant_count() -> None:
    dest_id = uuid.uuid4()
    mock_client = AsyncMock()
    mock_client.count = AsyncMock(return_value=SimpleNamespace(count=7))
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch("src.search.places_index.is_qdrant_available", return_value=True),
    ):
        assert await count_indexed(dest_id) == 7
