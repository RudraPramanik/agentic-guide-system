"""Generate and HTTP stay unchanged when planner_runs exists."""

from __future__ import annotations

import uuid

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func, select

from src.destinations.models import Destination
from src.places.models import Place
from src.planner.runs.models import PlannerRun
from src.trips.service import TripService


async def _seed_dest_and_places(db_session) -> tuple[Destination, list[Place]]:
    dest = Destination(
        name="Boundary City",
        country="IN",
        display_name="Boundary City",
        osm_place_id=f"relation/boundary-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
    )
    db_session.add(dest)
    await db_session.flush()
    place = Place(
        osm_id=f"node/boundary-{uuid.uuid4().hex[:8]}",
        name="Stop 0",
        category="attraction",
        tags={},
        location=from_shape(Point(88.263, 27.041), srid=4326),
        destination_id=dest.id,
    )
    db_session.add(place)
    await db_session.flush()
    return dest, [place]


def _complete_state(dest_id: uuid.UUID, places: list[Place]) -> dict:
    place = places[0]
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
                        "leg_polyline": "poly_leg_0",
                    }
                ],
                "total_distance_km": 1.0,
                "total_travel_min": 10,
                "day_polyline": "poly_day",
            }
        ],
    }


@pytest.mark.asyncio
async def test_save_from_state_inserts_no_planner_run(db_session) -> None:
    dest, places = await _seed_dest_and_places(db_session)
    trip = await TripService(db_session).save_from_state(
        _complete_state(dest.id, places),
        user_id=None,
        session_id="sess-no-run",
    )
    assert trip is not None
    count = (
        await db_session.execute(select(func.count()).select_from(PlannerRun))
    ).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_run_lookup_route_is_absent(client) -> None:
    response = await client.get(f"/api/v1/planner/runs/{uuid.uuid4()}")
    assert response.status_code == 404
