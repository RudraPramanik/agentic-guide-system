"""P3/V4/V5: places_index upsert / search / count contracts (mocked Qdrant)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from qdrant_client import models as qmodels

from src.search.places_index import (
    _canonical_text,
    count_indexed,
    search_places,
    search_places_with_diagnostics,
    upsert_place,
    upsert_places_batch,
)


def test_canonical_text_includes_name_and_category() -> None:
    place = SimpleNamespace(
        name="Tiger Hill",
        category="viewpoint",
        summary="Sunrise spot",
        enriched_tags=["photography", "sunrise"],
    )
    text = _canonical_text(place)
    assert "Tiger Hill" in text
    assert "viewpoint" in text
    assert "Sunrise spot" in text
    assert "photography" in text


def test_canonical_text_omits_empty_name() -> None:
    place = SimpleNamespace(
        name="",
        category=None,
        summary="Only summary",
        enriched_tags=[],
    )
    text = _canonical_text(place)
    assert text == "Only summary"
    assert "None" not in text


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
        patch(
            "src.search.places_index.collection_uses_hybrid_schema",
            return_value=False,
        ),
    ):
        await search_places("q", dest_id, top_k=5)
        kwargs = mock_client.query_points.await_args.kwargs
        filt: qmodels.Filter = kwargs["query_filter"]
        assert filt.must[0].match.value == str(dest_id)
        assert "prefetch" not in kwargs


@pytest.mark.asyncio
async def test_search_places_hybrid_uses_rrf_prefetch() -> None:
    dest_id = uuid.uuid4()
    mock_client = AsyncMock()
    mock_client.query_points = AsyncMock(
        return_value=SimpleNamespace(points=[])
    )
    sparse = qmodels.SparseVector(indices=[1, 2], values=[1.0, 1.0])
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch(
            "src.search.places_index.embed_text",
            new=AsyncMock(return_value=[0.0] * 384),
        ),
        patch("src.search.places_index.is_qdrant_available", return_value=True),
        patch(
            "src.search.places_index.collection_uses_hybrid_schema",
            return_value=True,
        ),
        patch("src.search.places_index.is_sparse_available", return_value=True),
        patch("src.search.places_index.encode_sparse", return_value=sparse),
        patch(
            "src.search.places_index.get_settings",
            return_value=SimpleNamespace(
                SEARCH_SPARSE_ENABLED=True,
                SEARCH_RRF_K=60,
                SEARCH_FUSION_DIAGNOSTICS=False,
                QDRANT_OPERATION_TIMEOUT_SECONDS=5.0,
            ),
        ),
        patch(
            "src.search.places_index.places_collection",
            return_value="places_v2",
        ),
    ):
        await search_places("Tiger Hill", dest_id, top_k=5)
        kwargs = mock_client.query_points.await_args.kwargs
        assert "prefetch" in kwargs
        assert len(kwargs["prefetch"]) == 2
        assert kwargs["prefetch"][0].filter.must[0].match.value == str(dest_id)
        assert isinstance(kwargs["query"], qmodels.FusionQuery)


@pytest.mark.asyncio
async def test_search_places_dense_only_when_sparse_disabled() -> None:
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
        patch(
            "src.search.places_index.collection_uses_hybrid_schema",
            return_value=True,
        ),
        patch(
            "src.search.places_index.get_settings",
            return_value=SimpleNamespace(
                SEARCH_SPARSE_ENABLED=False,
                SEARCH_RRF_K=60,
                SEARCH_FUSION_DIAGNOSTICS=False,
                QDRANT_OPERATION_TIMEOUT_SECONDS=5.0,
            ),
        ),
        patch(
            "src.search.places_index.places_collection",
            return_value="places_v2",
        ),
    ):
        await search_places("q", dest_id, top_k=5)
        kwargs = mock_client.query_points.await_args.kwargs
        assert "prefetch" not in kwargs
        assert kwargs["using"] == "dense"
        assert kwargs["query_filter"].must[0].match.value == str(dest_id)


@pytest.mark.asyncio
async def test_upsert_batch_hybrid_named_vectors_single_call() -> None:
    dest_id = uuid.uuid4()
    places = [
        SimpleNamespace(
            id=uuid.uuid4(),
            summary="S",
            enriched_tags=[],
            name="Tiger Hill",
            osm_id="1",
            category="viewpoint",
        ),
    ]
    mock_client = AsyncMock()
    mock_client.upsert = AsyncMock()
    sparse = qmodels.SparseVector(indices=[9], values=[1.0])
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch(
            "src.search.places_index.embed_batch",
            new=AsyncMock(return_value=[[0.1] * 384]),
        ),
        patch(
            "src.search.places_index.collection_uses_hybrid_schema",
            return_value=True,
        ),
        patch(
            "src.search.places_index.encode_sparse_batch",
            new=AsyncMock(return_value=[sparse]),
        ),
        patch(
            "src.search.places_index.places_collection",
            return_value="places_v2",
        ),
    ):
        assert await upsert_places_batch(places, dest_id) == 1
        assert mock_client.upsert.await_count == 1
        point = mock_client.upsert.await_args.kwargs["points"][0]
        assert isinstance(point.vector, dict)
        assert "dense" in point.vector
        assert "bm25" in point.vector


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


def _point(place_id: str, score: float = 1.0) -> SimpleNamespace:
    return SimpleNamespace(
        score=score,
        payload={"place_id": place_id, "name": place_id, "destination_id": "d"},
    )


@pytest.mark.asyncio
async def test_fusion_diagnostics_hybrid_records_three_orders() -> None:
    dest_id = uuid.uuid4()
    fused = [_point("f1", 0.9), _point("f2", 0.8)]
    dense = [_point("d1"), _point("f1")]
    sparse = [_point("s1"), _point("f2")]
    mock_client = AsyncMock()
    mock_client.query_points = AsyncMock(
        side_effect=[
            SimpleNamespace(points=fused),
            SimpleNamespace(points=dense),
            SimpleNamespace(points=sparse),
        ]
    )
    sparse_q = qmodels.SparseVector(indices=[1], values=[1.0])
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch(
            "src.search.places_index.embed_text",
            new=AsyncMock(return_value=[0.0] * 384),
        ),
        patch("src.search.places_index.is_qdrant_available", return_value=True),
        patch(
            "src.search.places_index.collection_uses_hybrid_schema",
            return_value=True,
        ),
        patch("src.search.places_index.is_sparse_available", return_value=True),
        patch("src.search.places_index.encode_sparse", return_value=sparse_q),
        patch(
            "src.search.places_index.get_settings",
            return_value=SimpleNamespace(
                SEARCH_SPARSE_ENABLED=True,
                SEARCH_RRF_K=60,
                SEARCH_FUSION_DIAGNOSTICS=True,
                QDRANT_OPERATION_TIMEOUT_SECONDS=5.0,
            ),
        ),
        patch(
            "src.search.places_index.places_collection",
            return_value="places_v2",
        ),
    ):
        outcome = await search_places_with_diagnostics("q", dest_id, top_k=2)
        assert [h.place_id for h in outcome.hits] == ["f1", "f2"]
        assert outcome.diagnostics is not None
        assert outcome.diagnostics["mode"] == "hybrid_rrf"
        assert outcome.diagnostics["fused_place_ids"] == ["f1", "f2"]
        assert outcome.diagnostics["dense_place_ids"] == ["d1", "f1"]
        assert outcome.diagnostics["sparse_place_ids"] == ["s1", "f2"]
        assert mock_client.query_points.await_count == 3


@pytest.mark.asyncio
async def test_fusion_diagnostics_dense_only_shape() -> None:
    dest_id = uuid.uuid4()
    mock_client = AsyncMock()
    mock_client.query_points = AsyncMock(
        return_value=SimpleNamespace(points=[_point("a"), _point("b")])
    )
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch(
            "src.search.places_index.embed_text",
            new=AsyncMock(return_value=[0.0] * 384),
        ),
        patch("src.search.places_index.is_qdrant_available", return_value=True),
        patch(
            "src.search.places_index.collection_uses_hybrid_schema",
            return_value=True,
        ),
        patch(
            "src.search.places_index.get_settings",
            return_value=SimpleNamespace(
                SEARCH_SPARSE_ENABLED=False,
                SEARCH_RRF_K=60,
                SEARCH_FUSION_DIAGNOSTICS=True,
                QDRANT_OPERATION_TIMEOUT_SECONDS=5.0,
            ),
        ),
        patch(
            "src.search.places_index.places_collection",
            return_value="places_v2",
        ),
    ):
        outcome = await search_places_with_diagnostics("q", dest_id, top_k=2)
        assert [h.place_id for h in outcome.hits] == ["a", "b"]
        assert outcome.diagnostics["mode"] == "dense_only"
        assert outcome.diagnostics["fused_place_ids"] == ["a", "b"]
        assert outcome.diagnostics["dense_place_ids"] == ["a", "b"]
        assert outcome.diagnostics["sparse_place_ids"] == []
        assert mock_client.query_points.await_count == 1


@pytest.mark.asyncio
async def test_fusion_diagnostics_subquery_failure_keeps_primary_hits() -> None:
    dest_id = uuid.uuid4()
    fused = [_point("keep-me")]
    mock_client = AsyncMock()

    async def _query_points(**kwargs):  # noqa: ANN003
        if "prefetch" in kwargs:
            return SimpleNamespace(points=fused)
        raise RuntimeError("diag down")

    mock_client.query_points = AsyncMock(side_effect=_query_points)
    sparse_q = qmodels.SparseVector(indices=[1], values=[1.0])
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch(
            "src.search.places_index.embed_text",
            new=AsyncMock(return_value=[0.0] * 384),
        ),
        patch("src.search.places_index.is_qdrant_available", return_value=True),
        patch(
            "src.search.places_index.collection_uses_hybrid_schema",
            return_value=True,
        ),
        patch("src.search.places_index.is_sparse_available", return_value=True),
        patch("src.search.places_index.encode_sparse", return_value=sparse_q),
        patch(
            "src.search.places_index.get_settings",
            return_value=SimpleNamespace(
                SEARCH_SPARSE_ENABLED=True,
                SEARCH_RRF_K=60,
                SEARCH_FUSION_DIAGNOSTICS=True,
                QDRANT_OPERATION_TIMEOUT_SECONDS=5.0,
            ),
        ),
        patch(
            "src.search.places_index.places_collection",
            return_value="places_v2",
        ),
    ):
        outcome = await search_places_with_diagnostics("q", dest_id, top_k=1)
        assert [h.place_id for h in outcome.hits] == ["keep-me"]
        assert outcome.diagnostics["mode"] == "hybrid_rrf"
        assert outcome.diagnostics["fused_place_ids"] == ["keep-me"]
        assert outcome.diagnostics["dense_place_ids"] == []
        assert outcome.diagnostics["sparse_place_ids"] == []


@pytest.mark.asyncio
async def test_fusion_diagnostics_flag_false_skips_extras() -> None:
    dest_id = uuid.uuid4()
    mock_client = AsyncMock()
    mock_client.query_points = AsyncMock(
        return_value=SimpleNamespace(points=[_point("x")])
    )
    sparse_q = qmodels.SparseVector(indices=[1], values=[1.0])
    with (
        patch("src.search.places_index.get_qdrant_client", return_value=mock_client),
        patch(
            "src.search.places_index.embed_text",
            new=AsyncMock(return_value=[0.0] * 384),
        ),
        patch("src.search.places_index.is_qdrant_available", return_value=True),
        patch(
            "src.search.places_index.collection_uses_hybrid_schema",
            return_value=True,
        ),
        patch("src.search.places_index.is_sparse_available", return_value=True),
        patch("src.search.places_index.encode_sparse", return_value=sparse_q),
        patch(
            "src.search.places_index.get_settings",
            return_value=SimpleNamespace(
                SEARCH_SPARSE_ENABLED=True,
                SEARCH_RRF_K=60,
                SEARCH_FUSION_DIAGNOSTICS=False,
                QDRANT_OPERATION_TIMEOUT_SECONDS=5.0,
            ),
        ),
        patch(
            "src.search.places_index.places_collection",
            return_value="places_v2",
        ),
    ):
        outcome = await search_places_with_diagnostics("q", dest_id, top_k=1)
        assert outcome.diagnostics is None
        assert [h.place_id for h in outcome.hits] == ["x"]
        assert mock_client.query_points.await_count == 1
