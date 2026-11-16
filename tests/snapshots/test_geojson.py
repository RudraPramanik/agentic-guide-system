"""Frozen public GeoJSON. The read does not call a routing provider."""

from __future__ import annotations

import pytest

from src.trips.service import TripService
from tests.snapshots.compare import assert_fixture
from tests.snapshots.seed import GUEST_SESSION, seed_saved_trip


@pytest.mark.asyncio
async def test_geojson_points_only_matches_fixture(client, db_session, monkeypatch) -> None:
    calls = {"n": 0}
    original = TripService._routing_or

    def _counting(self, routing=None):
        calls["n"] += 1
        return original(self, routing)

    monkeypatch.setattr(TripService, "_routing_or", _counting)
    _dest, _places, trip = await seed_saved_trip(
        db_session,
        session_id=GUEST_SESSION,
        polylines=False,
        osm_prefix="geo-points",
    )
    calls["n"] = 0

    response = await client.get(f"/api/v1/trips/{trip.id}/geojson")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert "success" not in body
    assert "data" not in body
    assert all(feature["geometry"]["type"] == "Point" for feature in body["features"])
    point = body["features"][0]
    assert set(point["properties"]) >= {
        "name",
        "day",
        "order",
        "suggested_start_time",
        "place_id",
        "trip_place_id",
    }
    lng, lat = point["geometry"]["coordinates"]
    assert isinstance(lng, float)
    assert isinstance(lat, float)
    assert calls["n"] == 0
    assert_fixture("geojson-points.json", body)


@pytest.mark.asyncio
async def test_geojson_linestring_matches_fixture(client, db_session) -> None:
    _dest, _places, trip = await seed_saved_trip(
        db_session,
        session_id=GUEST_SESSION,
        polylines=True,
        osm_prefix="geo-line",
    )

    response = await client.get(f"/api/v1/trips/{trip.id}/geojson")

    assert response.status_code == 200
    body = response.json()
    types = {feature["geometry"]["type"] for feature in body["features"]}
    assert "LineString" in types
    line = next(feature for feature in body["features"] if feature["geometry"]["type"] == "LineString")
    assert "day" in line["properties"]
    assert "trip_id" in line["properties"]
    assert_fixture("geojson-line.json", body)
