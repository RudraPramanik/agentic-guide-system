"""Idempotent trip save when a planner run is attached."""

from __future__ import annotations

import uuid

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func, select

from src.destinations.models import Destination
from src.places.models import Place
from src.planner.runs.models import PlannerRun, RunStatus
from src.planner.runs.service import PlannerRunService
from src.trips.models import Trip
from src.trips.service import TripService

pytestmark = pytest.mark.asyncio


async def _seed(db_session) -> tuple[Destination, Place]:
    dest = Destination(
        name="Idempotent City",
        country="IN",
        display_name="Idempotent City",
        osm_place_id=f"relation/idem-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=50,
    )
    db_session.add(dest)
    await db_session.flush()
    place = Place(
        osm_id=f"node/idem-{uuid.uuid4().hex[:8]}",
        name="Stop",
        category="attraction",
        tags={},
        location=from_shape(Point(88.263, 27.041), srid=4326),
        destination_id=dest.id,
    )
    db_session.add(place)
    await db_session.flush()
    return dest, place


def _state(dest_id: uuid.UUID, place: Place, **extra) -> dict:
    data = {
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
                "stops": [
                    {
                        "place_id": str(place.id),
                        "name": place.name,
                        "lat": 27.041,
                        "lng": 88.263,
                        "category": "attraction",
                        "order": 0,
                        "travel_time_min": 0,
                        "visit_duration_min": 60,
                        "suggested_start_time": "09:00",
                        "arrival_note": None,
                        "leg_polyline": "poly",
                    }
                ],
                "total_distance_km": 1.0,
                "total_travel_min": 10,
                "day_polyline": "day",
            }
        ],
    }
    data.update(extra)
    return data


async def test_idempotent_save_without_run_inserts_no_run(db_session) -> None:
    dest, place = await _seed(db_session)
    trip = await TripService(db_session).save_from_state(
        _state(dest.id, place),
        user_id=None,
        session_id="sess-no-run",
    )
    assert trip is not None
    count = (
        await db_session.execute(select(func.count()).select_from(PlannerRun))
    ).scalar_one()
    assert count == 0


async def test_idempotent_second_save_returns_the_first_trip(db_session) -> None:
    dest, place = await _seed(db_session)
    run, _ = await PlannerRunService(db_session).resolve(
        session_id="sess-save",
        user_id=None,
        idempotency_key="save-key",
        input_hash="a" * 64,
    )
    service = TripService(db_session)
    first = await service.save_from_state(
        _state(dest.id, place),
        user_id=None,
        session_id="sess-save",
        run_id=run.id,
    )
    second = await service.save_from_state(
        _state(dest.id, place),
        user_id=None,
        session_id="sess-save",
        run_id=run.id,
    )
    assert first is not None
    assert second is not None
    assert second.id == first.id
    trips = (await db_session.execute(select(func.count()).select_from(Trip))).scalar_one()
    assert trips == 1


async def test_idempotent_trip_id_is_set_before_return(db_session) -> None:
    dest, place = await _seed(db_session)
    run, _ = await PlannerRunService(db_session).resolve(
        session_id="sess-bind",
        user_id=None,
        idempotency_key="bind-key",
        input_hash="b" * 64,
    )
    trip = await TripService(db_session).save_from_state(
        _state(dest.id, place, used_geo_fallback=True),
        user_id=None,
        session_id="sess-bind",
        run_id=run.id,
    )
    assert trip is not None
    await db_session.refresh(run)
    assert run.trip_id == trip.id
    assert run.status == RunStatus.DEGRADED
