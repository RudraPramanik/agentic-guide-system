"""P6.3 trips HTTP — GeoJSON, ownership, claim, list auth."""

from __future__ import annotations

import uuid

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from src.auth.models import User
from src.auth.router import COOKIE_SESSION
from src.core.security.jwt import create_access_token
from src.destinations.models import Destination
from src.places.models import Place
from src.trips.polyline import decode_polyline
from src.trips.service import TripService


def _encode_polyline(coords: list[tuple[float, float]]) -> str:
    """Minimal encoder for test fixtures (pairs with decode_polyline)."""

    def _encode_signed(num: int) -> str:
        num = ~(num << 1) if num < 0 else (num << 1)
        chunks: list[str] = []
        while num >= 0x20:
            chunks.append(chr((0x20 | (num & 0x1F)) + 63))
            num >>= 5
        chunks.append(chr(num + 63))
        return "".join(chunks)

    result: list[str] = []
    prev_lat = 0
    prev_lng = 0
    for lat, lng in coords:
        ilat = int(round(lat * 1e5))
        ilng = int(round(lng * 1e5))
        result.append(_encode_signed(ilat - prev_lat))
        result.append(_encode_signed(ilng - prev_lng))
        prev_lat, prev_lng = ilat, ilng
    return "".join(result)


async def _seed_dest_and_places(db_session, n_places: int = 2) -> tuple[Destination, list[Place]]:
    dest = Destination(
        name="GeoJSON City",
        country="IN",
        display_name="GeoJSON City",
        osm_place_id=f"relation/geo-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
    )
    db_session.add(dest)
    await db_session.flush()

    places: list[Place] = []
    for i in range(n_places):
        place = Place(
            osm_id=f"node/geo-{uuid.uuid4().hex[:8]}",
            name=f"Stop {i}",
            category="attraction",
            tags={},
            location=from_shape(Point(88.263 + i * 0.01, 27.041), srid=4326),
            destination_id=dest.id,
        )
        db_session.add(place)
        places.append(place)
    await db_session.flush()
    return dest, places


def _state_with_polylines(
    dest_id: uuid.UUID,
    places: list[Place],
    *,
    use_real_polylines: bool,
) -> dict:
    stops = []
    for i, place in enumerate(places):
        if use_real_polylines:
            # Short leg around the stop
            lat0, lng0 = 27.041, 88.263 + i * 0.01
            poly = _encode_polyline([(lat0, lng0), (lat0 + 0.001, lng0 + 0.001)])
        else:
            poly = None
        stops.append(
            {
                "place_id": str(place.id),
                "name": place.name,
                "lat": 27.041,
                "lng": 88.263,
                "category": "attraction",
                "order": i,
                "travel_time_min": 10 * i,
                "visit_duration_min": 60,
                "suggested_start_time": f"{9 + i:02d}:00",
                "arrival_note": None,
                "leg_polyline": poly,
            }
        )
    return {
        "destination_id": str(dest_id),
        "interests": ["nature"],
        "budget": "moderate",
        "include_offbeat": False,
        "include_trekking": False,
        "plan_complete": True,
        "abort_triggered": False,
        "schedule": [
            {
                "day": 1,
                "stops": stops,
                "total_distance_km": 1.0,
                "total_travel_min": 10,
                "day_polyline": None,
            }
        ],
    }


def test_decode_polyline_roundtrip() -> None:
    encoded = _encode_polyline([(38.5, -120.2), (40.7, -120.95)])
    decoded = decode_polyline(encoded)
    assert len(decoded) == 2
    assert abs(decoded[0][0] - 38.5) < 1e-4
    assert abs(decoded[0][1] - (-120.2)) < 1e-4
    assert decode_polyline(None) == []
    assert decode_polyline("!!!") == [] or isinstance(decode_polyline("!!!"), list)


@pytest.mark.asyncio
async def test_geojson_linestring_when_polylines_present(client, db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=2)
    svc = TripService(db_session)
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    trip = await svc.save_from_state(
        _state_with_polylines(dest.id, places, use_real_polylines=True),
        user_id=None,
        session_id=session_id,
    )
    assert trip is not None

    response = await client.get(f"/api/v1/trips/{trip.id}/geojson")
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    types = {f["geometry"]["type"] for f in body["features"]}
    assert "Point" in types
    assert "LineString" in types
    # Not wrapped in ApiResponse
    assert "data" not in body


@pytest.mark.asyncio
async def test_geojson_points_only_when_no_polylines(client, db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=2)
    svc = TripService(db_session)
    trip = await svc.save_from_state(
        _state_with_polylines(dest.id, places, use_real_polylines=False),
        user_id=None,
        session_id=f"sess-{uuid.uuid4().hex[:8]}",
    )
    assert trip is not None

    response = await client.get(f"/api/v1/trips/{trip.id}/geojson")
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    geom_types = [f["geometry"]["type"] for f in body["features"]]
    assert geom_types.count("Point") == 2
    assert "LineString" not in geom_types


@pytest.mark.asyncio
async def test_get_trip_ownership_403(client, db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=1)
    svc = TripService(db_session)
    trip = await svc.save_from_state(
        _state_with_polylines(dest.id, places, use_real_polylines=False),
        user_id=None,
        session_id="owner-session",
    )
    assert trip is not None

    response = await client.get(
        f"/api/v1/trips/{trip.id}",
        cookies={COOKIE_SESSION: "wrong-session"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_trips_requires_auth(client) -> None:
    response = await client.get("/api/v1/trips")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_claim_success_wrong_session_and_reclaim(client, db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=1)
    user = User(
        email=f"claim-http-{uuid.uuid4().hex[:8]}@wandr.dev",
        name="Claimer",
        google_id=f"g-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    session_id = f"sess-claim-{uuid.uuid4().hex[:8]}"
    svc = TripService(db_session)
    trip = await svc.save_from_state(
        _state_with_polylines(dest.id, places, use_real_polylines=False),
        user_id=None,
        session_id=session_id,
    )
    assert trip is not None

    token = create_access_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    bad = await client.post(
        f"/api/v1/trips/{trip.id}/claim",
        headers=headers,
        cookies={COOKIE_SESSION: "wrong"},
    )
    assert bad.status_code == 403

    ok = await client.post(
        f"/api/v1/trips/{trip.id}/claim",
        headers=headers,
        cookies={COOKIE_SESSION: session_id},
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["user_id"] == str(user.id)

    again = await client.post(
        f"/api/v1/trips/{trip.id}/claim",
        headers=headers,
        cookies={COOKIE_SESSION: session_id},
    )
    assert again.status_code == 409
    assert again.json()["code"] == "trip_already_claimed"
