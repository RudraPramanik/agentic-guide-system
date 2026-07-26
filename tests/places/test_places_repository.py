"""Place repository geography radius tests."""

from __future__ import annotations

import uuid

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from src.destinations.models import Destination
from src.places.models import Place
from src.places.repository import PlaceRepository


@pytest.mark.asyncio
async def test_find_within_radius_respects_geography_units(db_session) -> None:
    """~3 km east of origin should match 5 km radius and miss 1 km radius."""
    origin_lat, origin_lng = 27.041, 88.263
    # ~0.027 degrees longitude ≈ 3 km near this latitude
    place_lat, place_lng = 27.041, 88.290

    dest = Destination(
        name="Radius City",
        country="IN",
        display_name="Radius City",
        osm_place_id=f"relation/radius-{uuid.uuid4().hex[:8]}",
        lat=origin_lat,
        lng=origin_lng,
    )
    db_session.add(dest)
    await db_session.flush()

    place = Place(
        osm_id=f"node/radius-{uuid.uuid4().hex[:8]}",
        name="Nearby POI",
        category="attraction",
        tags={},
        location=from_shape(Point(place_lng, place_lat), srid=4326),
        destination_id=dest.id,
    )
    db_session.add(place)
    await db_session.flush()

    repo = PlaceRepository(db_session)
    within_5 = await repo.find_within_radius(origin_lat, origin_lng, 5.0)
    within_1 = await repo.find_within_radius(origin_lat, origin_lng, 1.0)

    assert any(p.id == place.id for p in within_5)
    assert all(p.id != place.id for p in within_1)
