"""Destination repository upsert tests."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.destinations.models import Destination
from src.destinations.repository import DestinationRepository
from src.geo.schemas import GeocodedPlace


def _geocoded(osm_place_id: str, name: str = "Race City") -> GeocodedPlace:
    return GeocodedPlace(
        name=name,
        lat=27.041,
        lng=88.263,
        osm_place_id=osm_place_id,
        country="IN",
        display_name=f"{name}, India",
    )


@pytest.mark.asyncio
async def test_upsert_from_geocoded_is_idempotent(db_session) -> None:
    osm_id = f"relation/idem-{uuid.uuid4().hex[:8]}"
    geo = _geocoded(osm_id)
    repo = DestinationRepository(db_session)

    first = await repo.upsert_from_geocoded(geo)
    second = await repo.upsert_from_geocoded(geo)

    assert first.id == second.id


@pytest.mark.asyncio
async def test_upsert_from_geocoded_does_not_reset_counters(db_session) -> None:
    osm_id = f"relation/counters-{uuid.uuid4().hex[:8]}"
    geo = _geocoded(osm_id, name="Counter City")
    repo = DestinationRepository(db_session)

    dest = await repo.upsert_from_geocoded(geo)
    await repo.update(
        dest.id,
        {"place_count": 50, "enriched_count": 7, "indexed_count": 3},
    )

    again = await repo.upsert_from_geocoded(
        _geocoded(osm_id, name="Counter City Updated")
    )
    await db_session.refresh(again)

    assert again.id == dest.id
    assert again.place_count == 50
    assert again.enriched_count == 7
    assert again.indexed_count == 3
    assert again.name == "Counter City Updated"


@pytest.mark.asyncio
async def test_upsert_from_geocoded_concurrent_race(test_engine) -> None:
    osm_id = f"relation/race-{uuid.uuid4().hex[:8]}"
    geo = _geocoded(osm_id, name="Concurrent City")
    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def worker() -> uuid.UUID:
        async with factory() as session:
            dest = await DestinationRepository(session).upsert_from_geocoded(geo)
            await session.commit()
            return dest.id

    ids = await asyncio.wait_for(asyncio.gather(worker(), worker()), timeout=10.0)

    assert ids[0] == ids[1]
    async with factory() as session:
        count = (
            await session.execute(
                select(func.count())
                .select_from(Destination)
                .where(Destination.osm_place_id == osm_id)
            )
        ).scalar_one()
    assert count == 1
