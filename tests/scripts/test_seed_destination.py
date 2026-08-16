"""Seed script failure-boundary tests — no network, uses wandr_test."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from scripts.seed_destination import seed_destination, seed_destination_into, seed_places
from src.destinations.models import Destination
from src.geo.schemas import GeocodedPlace, RawPOI
from src.places.repository import PlaceRepository


def _poi(osm_id: str, name: str = "POI") -> RawPOI:
    return RawPOI(
        osm_id=osm_id,
        name=name,
        lat=27.04,
        lng=88.26,
        category="attraction",
        raw_tags={},
    )


def _geocoded(suffix: str = "a") -> GeocodedPlace:
    return GeocodedPlace(
        name=f"SeedTest-{suffix}",
        lat=27.041,
        lng=88.263,
        osm_place_id=f"relation/seed-{suffix}-{uuid.uuid4().hex[:8]}",
        country="IN",
        display_name=f"SeedTest-{suffix}, India",
    )


@pytest.mark.asyncio
async def test_seed_survives_partial_poi_failure(db_session, mocker) -> None:
    dest = Destination(
        name="Partial Seed City",
        country="IN",
        display_name="Partial Seed City",
        osm_place_id=f"relation/partial-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
    )
    db_session.add(dest)
    await db_session.flush()

    pois = [_poi("node/1", "A"), _poi("node/2", "B"), _poi("node/3", "C")]
    real_upsert = PlaceRepository.upsert_from_poi

    async def flaky_upsert(self, poi, destination_id):
        if poi.osm_id == "node/2":
            raise RuntimeError("simulated POI failure")
        return await real_upsert(self, poi, destination_id)

    mocker.patch.object(PlaceRepository, "upsert_from_poi", flaky_upsert)

    success = await seed_places(db_session, dest.id, pois)

    assert success == 2


@pytest.mark.asyncio
async def test_seed_continues_when_overpass_returns_empty(db_session, mocker) -> None:
    geocoded = _geocoded("empty")
    mocker.patch(
        "src.destinations.ingest.geocode",
        new=AsyncMock(return_value=geocoded),
    )
    mocker.patch(
        "src.destinations.ingest.fetch_pois",
        new=AsyncMock(return_value=[]),
    )

    dest, success, poi_total = await seed_destination_into(
        db_session, "Empty Overpass Town", 30.0
    )

    assert success == 0
    assert poi_total == 0
    assert dest.place_count == 0
    assert dest.osm_place_id == geocoded.osm_place_id


@pytest.mark.asyncio
async def test_seed_geocode_failure_exits_1(mocker) -> None:
    mocker.patch(
        "scripts.seed_destination.geocode",
        new=AsyncMock(return_value=None),
    )

    code = await seed_destination("XyzzyNonexistentPlace99999", 30.0)

    assert code == 1
