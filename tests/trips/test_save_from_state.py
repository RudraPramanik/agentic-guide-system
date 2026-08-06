"""TripService save_from_state UoW + ownership/claim tests (P6.1)."""

from __future__ import annotations

import uuid

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func, select

from src.auth.models import User
from src.destinations.models import Destination
from src.places.models import Place
from src.trips.exceptions import TripAlreadyClaimedError, TripForbiddenError
from src.trips.models import Trip, TripStatus
from src.trips.repository import TripRepository
from src.trips.service import TripService, _preferences_from_state


async def _seed_dest_and_places(db_session, n_places: int = 2) -> tuple[Destination, list[Place]]:
    dest = Destination(
        name="Trip Test City",
        country="IN",
        display_name="Trip Test City",
        osm_place_id=f"relation/trip-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
    )
    db_session.add(dest)
    await db_session.flush()

    places: list[Place] = []
    for i in range(n_places):
        place = Place(
            osm_id=f"node/trip-{uuid.uuid4().hex[:8]}",
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


def _complete_state(dest_id: uuid.UUID, places: list[Place]) -> dict:
    stops = []
    for i, place in enumerate(places):
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
                "leg_polyline": f"poly_leg_{i}",
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
                "day_polyline": "poly_day",
            }
        ],
    }


@pytest.mark.asyncio
async def test_save_from_state_persists_base_prefs(db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=1)
    svc = TripService(db_session)
    state = _complete_state(dest.id, places)
    state["base_lat"] = 27.05
    state["base_lng"] = 88.27

    trip = await svc.save_from_state(state, user_id=None, session_id="sess-base")
    assert trip is not None
    assert trip.preferences["base_lat"] == 27.05
    assert trip.preferences["base_lng"] == 88.27
    assert trip.preferences["interests"] == ["nature"]


@pytest.mark.asyncio
async def test_save_from_state_omits_base_when_absent(db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=1)
    svc = TripService(db_session)
    trip = await svc.save_from_state(
        _complete_state(dest.id, places),
        user_id=None,
        session_id="sess-no-base",
    )
    assert trip is not None
    assert "base_lat" not in trip.preferences
    assert "base_lng" not in trip.preferences


def test_preferences_from_state_includes_base_when_coercible() -> None:
    prefs = _preferences_from_state(
        {
            "interests": ["nature"],
            "budget": "moderate",
            "include_offbeat": False,
            "include_trekking": False,
            "base_lat": "27.05",
            "base_lng": 88.27,
        }
    )
    assert prefs["base_lat"] == 27.05
    assert prefs["base_lng"] == 88.27
    assert prefs["interests"] == ["nature"]


def test_preferences_from_state_omits_base_when_incomplete() -> None:
    prefs = _preferences_from_state(
        {
            "interests": [],
            "budget": None,
            "include_offbeat": None,
            "include_trekking": None,
            "base_lat": 27.0,
            # base_lng missing
        }
    )
    assert "base_lat" not in prefs
    assert "base_lng" not in prefs

    prefs_bad = _preferences_from_state(
        {
            "interests": [],
            "budget": None,
            "include_offbeat": None,
            "include_trekking": None,
            "base_lat": "nope",
            "base_lng": 88.0,
        }
    )
    assert "base_lat" not in prefs_bad
    assert "base_lng" not in prefs_bad


def test_resolve_base_prefs_win() -> None:
    trip = Trip(preferences={"base_lat": 1.5, "base_lng": 2.5})
    dest = Destination(lat=27.0, lng=88.0)
    assert TripService._resolve_base(trip, dest) == (1.5, 2.5)


def test_resolve_base_falls_back_to_destination() -> None:
    dest = Destination(lat=27.041, lng=88.263)
    trip_missing = Trip(preferences={"interests": []})
    assert TripService._resolve_base(trip_missing, dest) == (27.041, 88.263)

    trip_none_prefs = Trip(preferences=None)
    assert TripService._resolve_base(trip_none_prefs, dest) == (27.041, 88.263)

    trip_non_numeric = Trip(preferences={"base_lat": "x", "base_lng": "y"})
    assert TripService._resolve_base(trip_non_numeric, dest) == (27.041, 88.263)

    trip_bool = Trip(preferences={"base_lat": True, "base_lng": False})
    assert TripService._resolve_base(trip_bool, dest) == (27.041, 88.263)


@pytest.mark.asyncio
async def test_save_from_state_persists_polylines(db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=2)
    svc = TripService(db_session)
    session_id = f"sess-{uuid.uuid4().hex[:12]}"

    trip = await svc.save_from_state(
        _complete_state(dest.id, places),
        user_id=None,
        session_id=session_id,
    )
    assert trip is not None
    assert trip.status == TripStatus.COMPLETE
    assert trip.user_id is None
    assert trip.session_id == session_id

    loaded = await TripRepository(db_session).get_with_places(trip.id)
    assert loaded is not None
    assert len(loaded.places) == 2
    assert [p.polyline for p in loaded.places] == ["poly_leg_0", "poly_leg_1"]
    assert all(p.place is not None for p in loaded.places)
    assert loaded.places[0].place.name == "Stop 0"


@pytest.mark.asyncio
async def test_save_from_state_skips_empty_schedule(db_session) -> None:
    dest, _ = await _seed_dest_and_places(db_session, n_places=1)
    svc = TripService(db_session)
    result = await svc.save_from_state(
        {
            "destination_id": str(dest.id),
            "plan_complete": False,
            "abort_triggered": False,
            "schedule": [],
            "interests": [],
        },
        user_id=None,
        session_id="sess-empty",
    )
    assert result is None
    count = (
        await db_session.execute(select(func.count()).select_from(Trip))
    ).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_partial_insert_rolls_back(db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=1)
    svc = TripService(db_session)

    async def _boom(_rows):
        raise RuntimeError("forced mid-insert fail")

    svc.repo.create_trip_places = _boom  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="forced mid-insert fail"):
        await svc.save_from_state(
            _complete_state(dest.id, places),
            user_id=None,
            session_id="sess-rollback",
        )

    count = (
        await db_session.execute(select(func.count()).select_from(Trip))
    ).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_assert_can_access_guest_and_owner(db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=1)
    svc = TripService(db_session)
    session_id = "sess-access"
    trip = await svc.save_from_state(
        _complete_state(dest.id, places),
        user_id=None,
        session_id=session_id,
    )
    assert trip is not None

    svc.assert_can_access(trip, user_id=None, session_id=session_id)

    with pytest.raises(TripForbiddenError):
        svc.assert_can_access(trip, user_id=None, session_id="wrong")

    with pytest.raises(TripForbiddenError):
        svc.assert_can_access(trip, user_id=uuid.uuid4(), session_id="wrong")


@pytest.mark.asyncio
async def test_claim_for_user_success_and_conflicts(db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session, n_places=1)
    user = User(
        email=f"claim-{uuid.uuid4().hex[:8]}@wandr.dev",
        name="Claimer",
        google_id=f"g-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    svc = TripService(db_session)
    session_id = "sess-claim"
    trip = await svc.save_from_state(
        _complete_state(dest.id, places),
        user_id=None,
        session_id=session_id,
    )
    assert trip is not None

    with pytest.raises(TripForbiddenError):
        await svc.claim_for_user(trip, user.id, "wrong-session")
    await db_session.refresh(trip)
    assert trip.user_id is None

    claimed = await svc.claim_for_user(trip, user.id, session_id)
    assert claimed.user_id == user.id

    with pytest.raises(TripAlreadyClaimedError) as exc_info:
        await svc.claim_for_user(claimed, user.id, session_id)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "trip_already_claimed"
