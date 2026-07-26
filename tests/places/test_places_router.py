"""Places HTTP router tests."""

from __future__ import annotations

import uuid

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select

from src.destinations.models import Destination
from src.places.models import Place


async def _seed_destination_with_places(db_session, *, count: int = 12) -> Destination:
    dest = Destination(
        name="Places Town",
        country="IN",
        display_name="Places Town",
        osm_place_id=f"relation/places-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=count,
    )
    db_session.add(dest)
    await db_session.flush()

    for i in range(count):
        db_session.add(
            Place(
                osm_id=f"node/places-{uuid.uuid4().hex[:8]}-{i}",
                name=f"Place {i}",
                category="attraction",
                tags={},
                location=from_shape(Point(88.263 + i * 0.001, 27.041), srid=4326),
                destination_id=dest.id,
            )
        )
    await db_session.flush()
    return dest


@pytest.mark.asyncio
async def test_list_places_paginated(client, db_session) -> None:
    dest = await _seed_destination_with_places(db_session, count=12)

    response = await client.get(
        f"/api/v1/places?destination_id={dest.id}&page=2&size=5"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 12
    assert body["page"] == 2
    assert body["size"] == 5
    assert body["pages"] == 3
    assert body["has_next"] is True
    assert body["has_prev"] is True
    assert len(body["items"]) == 5
    assert "lat" in body["items"][0]
    assert "lng" in body["items"][0]


@pytest.mark.asyncio
async def test_get_place_404(client) -> None:
    response = await client.get(
        "/api/v1/places/00000000-0000-0000-0000-000000000001"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


@pytest.mark.asyncio
async def test_get_place_success(client, db_session) -> None:
    dest = await _seed_destination_with_places(db_session, count=1)
    place = (
        await db_session.execute(select(Place).where(Place.destination_id == dest.id))
    ).scalar_one()

    response = await client.get(f"/api/v1/places/{place.id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(place.id)
    assert data["name"] == place.name
    assert data["lat"] != 0
    assert data["lng"] != 0


@pytest.mark.asyncio
async def test_list_places_unknown_destination_404(client) -> None:
    response = await client.get(
        "/api/v1/places?destination_id=00000000-0000-0000-0000-000000000001&page=1"
    )

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert "items" not in body
