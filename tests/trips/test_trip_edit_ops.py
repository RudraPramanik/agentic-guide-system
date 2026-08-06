"""TripService P7.2 day-surgery Fake tests (no HTTP, no live OSRM)."""

from __future__ import annotations

import uuid

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func, select

from src.auth.models import User
from src.destinations.models import Destination
from src.places.models import Place
from src.travel_engine.travel_rules import MAX_DAILY_TRAVEL_MIN
from src.trips.exceptions import (
    TripEditValidationError,
    TripStopConflictError,
)
from src.trips.models import EditType, Trip, TripEditEvent, TripPlace, TripStatus
from src.trips.service import TripService
from tests.travel_engine.fake_routing import FakeRoutingProvider


async def _seed_owned_trip(
    db_session,
    *,
    n_places: int = 3,
    categories: list[str] | None = None,
) -> tuple[User, Destination, list[Place], Trip]:
    user = User(
        email=f"edit-{uuid.uuid4().hex[:8]}@example.com",
        name="Editor",
        google_id=f"g-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(user)
    await db_session.flush()

    dest = Destination(
        name="Edit Test City",
        country="IN",
        display_name="Edit Test City",
        osm_place_id=f"relation/edit-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
    )
    db_session.add(dest)
    await db_session.flush()

    cats = categories or ["attraction"] * n_places
    places: list[Place] = []
    for i in range(n_places):
        place = Place(
            osm_id=f"node/edit-{uuid.uuid4().hex[:8]}",
            name=f"Stop {i}",
            category=cats[i] if i < len(cats) else "attraction",
            tags={},
            enriched_tags=[],
            location=from_shape(Point(88.263 + i * 0.01, 27.041), srid=4326),
            destination_id=dest.id,
        )
        db_session.add(place)
        places.append(place)
    await db_session.flush()

    trip = Trip(
        user_id=user.id,
        session_id=f"sess-{uuid.uuid4().hex[:8]}",
        destination_id=dest.id,
        days=1,
        preferences={"base_lat": 27.041, "base_lng": 88.263, "interests": []},
        status=TripStatus.COMPLETE,
    )
    db_session.add(trip)
    await db_session.flush()

    for i, place in enumerate(places):
        db_session.add(
            TripPlace(
                trip_id=trip.id,
                place_id=place.id,
                day_number=1,
                order_in_day=i + 1,
                travel_time_min=10,
                visit_duration_min=60,
                suggested_start_time=f"{8 + i:02d}:00",
                polyline=f"old_poly_{i}",
            )
        )
    await db_session.commit()

    loaded = await TripService(db_session).repo.get_with_places(trip.id)
    assert loaded is not None
    return user, dest, places, loaded


@pytest.mark.asyncio
async def test_reorder_preserves_order_and_polylines(db_session) -> None:
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=3)
    # Reverse order
    new_order = [places[2].id, places[1].id, places[0].id]
    fake = FakeRoutingProvider()
    svc = TripService(db_session, routing=fake)

    updated = await svc.reorder_stops(
        trip.id, 1, new_order, user.id, routing=fake
    )

    day_places = sorted(
        [tp for tp in updated.places if tp.day_number == 1],
        key=lambda tp: tp.order_in_day,
    )
    assert [tp.place_id for tp in day_places] == new_order
    assert all(tp.polyline and tp.polyline.startswith("poly_") for tp in day_places)

    events = (
        await db_session.execute(
            select(TripEditEvent).where(TripEditEvent.trip_id == trip.id)
        )
    ).scalars().all()
    assert len(events) == 1
    assert events[0].edit_type == EditType.REORDER


@pytest.mark.asyncio
async def test_remove_last_stop_rejected(db_session) -> None:
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=1)
    svc = TripService(db_session, routing=FakeRoutingProvider())

    with pytest.raises(TripEditValidationError) as exc:
        await svc.remove_stop(trip.id, 1, places[0].id, user.id)

    assert exc.value.code == "day_would_be_empty"
    count = (
        await db_session.execute(
            select(func.count()).select_from(TripPlace).where(
                TripPlace.trip_id == trip.id
            )
        )
    ).scalar_one()
    assert count == 1
    events = (
        await db_session.execute(
            select(func.count()).select_from(TripEditEvent).where(
                TripEditEvent.trip_id == trip.id
            )
        )
    ).scalar_one()
    assert events == 0


@pytest.mark.asyncio
async def test_add_duplicate_conflict(db_session) -> None:
    user, _dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    svc = TripService(db_session, routing=FakeRoutingProvider())

    with pytest.raises(TripStopConflictError) as exc:
        await svc.add_stop(trip.id, 1, places[0].id, user.id)

    assert exc.value.status_code == 409
    assert exc.value.code == "stop_already_on_trip"


@pytest.mark.asyncio
async def test_add_that_would_drop_rejects_without_mutation(db_session) -> None:
    user, dest, places, trip = await _seed_owned_trip(db_session, n_places=2)
    extra = Place(
        osm_id=f"node/edit-extra-{uuid.uuid4().hex[:8]}",
        name="Extra Dropper",
        category="attraction",
        tags={},
        enriched_tags=[],
        location=from_shape(Point(88.30, 27.05), srid=4326),
        destination_id=dest.id,
    )
    db_session.add(extra)
    await db_session.commit()

    before_count = (
        await db_session.execute(
            select(func.count()).select_from(TripPlace).where(
                TripPlace.trip_id == trip.id
            )
        )
    ).scalar_one()

    # High hop duration forces drop-retry when 3 stops are optimized.
    fake = FakeRoutingProvider(default_duration_min=MAX_DAILY_TRAVEL_MIN + 1)
    svc = TripService(db_session, routing=fake)

    with pytest.raises(TripEditValidationError) as exc:
        await svc.add_stop(trip.id, 1, extra.id, user.id, routing=fake)

    assert exc.value.code == "edit_would_drop_other_stops"
    after_count = (
        await db_session.execute(
            select(func.count()).select_from(TripPlace).where(
                TripPlace.trip_id == trip.id
            )
        )
    ).scalar_one()
    assert after_count == before_count
    events = (
        await db_session.execute(
            select(func.count()).select_from(TripEditEvent).where(
                TripEditEvent.trip_id == trip.id
            )
        )
    ).scalar_one()
    assert events == 0
