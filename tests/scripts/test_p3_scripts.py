"""P3: enrich/index script helpers (mocked externals + limit guard)."""

from __future__ import annotations

import math
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from src.places.models import Place
from scripts.enrich_places import enrich_places
from scripts.index_places import index_places


def test_enrich_limit_zero_does_not_apply_sql_limit() -> None:
    stmt = select(Place)
    limit = 0
    if limit and limit > 0:
        stmt = stmt.limit(limit)
    assert stmt._limit_clause is None


@pytest.mark.asyncio
async def test_enrich_places_continues_when_parse_returns_none() -> None:
    place_ok = SimpleNamespace(id=uuid.uuid4())
    place_fail = SimpleNamespace(id=uuid.uuid4())
    parsed = SimpleNamespace(summary="S", tags=["photography"])

    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [place_fail, place_ok]
    session.execute = AsyncMock(return_value=result)
    session.scalar = AsyncMock(return_value=1)
    session.begin_nested = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(),
            __aexit__=AsyncMock(return_value=False),
        )
    )

    dest_id = uuid.uuid4()
    with (
        patch("scripts.enrich_places.get_settings") as mock_settings,
        patch("scripts.enrich_places.PlaceService") as MockSvc,
        patch("scripts.enrich_places.DestinationRepository") as MockDestRepo,
    ):
        mock_settings.return_value.ENRICH_BATCH_LLM_CONCURRENCY = 2
        svc = MockSvc.return_value
        svc._call_llm_and_parse = AsyncMock(side_effect=[None, parsed])
        svc.repo.update = AsyncMock()
        MockDestRepo.return_value.update = AsyncMock()

        success = await enrich_places(session, dest_id, batch_size=10, limit=0)
        assert success == 1
        assert svc.repo.update.await_count == 1


@pytest.mark.asyncio
async def test_index_places_uses_batch_upsert_and_count_indexed() -> None:
    places = [SimpleNamespace(id=uuid.uuid4(), summary="S") for _ in range(5)]
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = places
    session.execute = AsyncMock(return_value=result)

    dest_id = uuid.uuid4()
    with (
        patch(
            "scripts.index_places.upsert_places_batch",
            new=AsyncMock(return_value=2),
        ) as mock_batch,
        patch(
            "scripts.index_places.count_indexed",
            new=AsyncMock(return_value=99),
        ) as mock_count,
        patch("scripts.index_places.DestinationRepository") as MockDestRepo,
    ):
        MockDestRepo.return_value.update = AsyncMock()
        success = await index_places(session, dest_id, batch_size=2, limit=0)
        assert success == 6  # 3 chunks * 2
        assert mock_batch.await_count == math.ceil(5 / 2)
        MockDestRepo.return_value.update.assert_awaited_with(
            dest_id, {"indexed_count": 99}
        )
        assert mock_count.await_count == 1
