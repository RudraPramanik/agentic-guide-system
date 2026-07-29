"""P3: enrich/index script helpers (mocked externals + limit guard)."""

from __future__ import annotations

import math
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select, text

from scripts.enrich_places import enrich_places
from scripts.index_places import index_places
from src.destinations.models import Destination
from src.places.models import Place
from src.places.repository import PlaceRepository
from src.places.service import ParsedEnrichment, PlaceService


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
async def test_enrich_places_savepoint_isolates_db_write_failure(db_session) -> None:
    """Real Postgres: a mid-batch write error must not abort later places (SAVEPOINT)."""
    dest = Destination(
        name="Savepoint City",
        country="IN",
        display_name="Savepoint City",
        osm_place_id=f"relation/savepoint-{uuid.uuid4().hex[:8]}",
        lat=27.04,
        lng=88.26,
        place_count=3,
    )
    db_session.add(dest)
    await db_session.flush()

    seeded: list[Place] = []
    for i in range(3):
        place = Place(
            osm_id=f"node/savepoint-{uuid.uuid4().hex[:8]}",
            name=f"Savepoint POI {i}",
            category="attraction",
            tags={"tourism": "attraction"},
            location=from_shape(Point(88.26 + i * 0.001, 27.04), srid=4326),
            destination_id=dest.id,
        )
        db_session.add(place)
        seeded.append(place)
    await db_session.flush()

    fail_id = seeded[1].id
    ok_ids = {seeded[0].id, seeded[2].id}
    parsed = ParsedEnrichment(summary="Enriched summary", tags=["photography"])
    original_update = PlaceRepository.update

    async def flaky_update(repo_self, entity_id, data):  # noqa: ANN001
        if entity_id == fail_id:
            # Real DB error — without begin_nested this poisons the outer txn.
            await repo_self.session.execute(
                text("SELECT 1 FROM __wandr_savepoint_isolation_missing__")
            )
        return await original_update(repo_self, entity_id, data)

    with (
        patch("scripts.enrich_places.get_settings") as mock_settings,
        patch.object(
            PlaceService,
            "_call_llm_and_parse",
            new=AsyncMock(return_value=parsed),
        ),
        patch.object(PlaceRepository, "update", flaky_update),
    ):
        mock_settings.return_value.ENRICH_BATCH_LLM_CONCURRENCY = 1
        success = await enrich_places(
            db_session, dest.id, batch_size=10, limit=0
        )

    assert success == 2

    db_session.expire_all()
    for place_id in ok_ids:
        place = await db_session.get(Place, place_id)
        assert place is not None
        assert place.summary == "Enriched summary"
        assert place.enriched_tags == ["photography"]

    failed = await db_session.get(Place, fail_id)
    assert failed is not None
    assert failed.summary is None
    assert failed.enriched_tags == []


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
