"""Fixed seeds for snapshot tests. Coordinates and names are constants."""

from __future__ import annotations

import uuid

from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from src.auth.models import User
from src.core.security.jwt import create_access_token
from src.destinations.models import Destination
from src.places.models import Place
from src.trips.service import TripService

GUEST_SESSION = "snapshot-guest-session"
_NS = uuid.UUID("11111111-1111-4111-8111-111111111111")


def stable_id(key: str) -> uuid.UUID:
    return uuid.uuid5(_NS, key)


def encode_polyline(coords: list[tuple[float, float]]) -> str:
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


async def seed_destination(
    db_session,
    *,
    name: str,
    osm_place_id: str,
    place_count: int = 0,
    enriched_count: int = 0,
    indexed_count: int = 0,
) -> Destination:
    dest = Destination(
        id=stable_id(osm_place_id),
        name=name,
        country="IN",
        display_name=name,
        osm_place_id=osm_place_id,
        lat=27.0,
        lng=88.25,
        place_count=place_count,
        enriched_count=enriched_count,
        indexed_count=indexed_count,
    )
    db_session.add(dest)
    await db_session.flush()
    return dest


async def seed_place(
    db_session,
    dest: Destination,
    *,
    name: str,
    osm_id: str,
    lng: float,
    lat: float,
) -> Place:
    place = Place(
        id=stable_id(osm_id),
        osm_id=osm_id,
        name=name,
        category="attraction",
        tags={},
        enriched_tags=[],
        location=from_shape(Point(lng, lat), srid=4326),
        destination_id=dest.id,
    )
    db_session.add(place)
    await db_session.flush()
    return place


def _stop(place: Place, order: int, *, polyline: str | None) -> dict:
    return {
        "place_id": str(place.id),
        "name": place.name,
        "lat": 27.0,
        "lng": 88.25,
        "category": "attraction",
        "order": order,
        "travel_time_min": 10,
        "visit_duration_min": 60,
        "suggested_start_time": f"{8 + order:02d}:00",
        "arrival_note": None,
        "leg_polyline": polyline,
    }


def trip_state(dest: Destination, places: list[Place], *, polylines: bool) -> dict:
    stops = []
    for index, place in enumerate(places, start=1):
        encoded = None
        if polylines:
            encoded = encode_polyline([(27.0, 88.25), (27.001, 88.251)])
        stops.append(_stop(place, index, polyline=encoded))
    return {
        "destination_id": str(dest.id),
        "interests": ["nature"],
        "budget": "moderate",
        "include_offbeat": False,
        "include_trekking": False,
        "base_lat": 27.0,
        "base_lng": 88.25,
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


async def seed_saved_trip(
    db_session,
    *,
    session_id: str,
    user_id: uuid.UUID | None = None,
    polylines: bool = False,
    n_places: int = 2,
    osm_prefix: str = "snapshot",
):
    dest = await seed_destination(
        db_session,
        name="Snapshot City",
        osm_place_id=f"relation/{osm_prefix}",
        place_count=12,
    )
    places = []
    for index in range(n_places):
        places.append(
            await seed_place(
                db_session,
                dest,
                name=f"Stop {index}",
                osm_id=f"node/{osm_prefix}-{index}",
                lng=88.25 + (index * 0.01),
                lat=27.0,
            )
        )
    trip = await TripService(db_session).save_from_state(
        trip_state(dest, places, polylines=polylines),
        user_id=user_id,
        session_id=session_id,
    )
    assert trip is not None
    return dest, places, trip


async def seed_owner(db_session, *, email: str, google_id: str) -> tuple[User, str]:
    user = User(
        id=stable_id(google_id),
        email=email,
        name="Snapshot Owner",
        google_id=google_id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    token = create_access_token(user.id, user.email)
    return user, token
