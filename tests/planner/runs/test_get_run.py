"""GET /api/v1/planner/runs/{run_id} ownership."""

from __future__ import annotations

import uuid

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from src.destinations.models import Destination
from src.places.models import Place
from src.planner.runs.service import PlannerRunService
from src.trips.service import TripService

pytestmark = pytest.mark.asyncio


async def _state(db_session) -> dict:
    dest = Destination(
        name="Get City",
        country="IN",
        display_name="Get City",
        osm_place_id=f"relation/get-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=50,
    )
    db_session.add(dest)
    await db_session.flush()
    place = Place(
        osm_id=f"node/get-{uuid.uuid4().hex[:8]}",
        name="Get Stop",
        category="attraction",
        tags={},
        location=from_shape(Point(88.263, 27.041), srid=4326),
        destination_id=dest.id,
    )
    db_session.add(place)
    await db_session.flush()
    return {
        "destination_id": str(dest.id),
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
                        "order": 0,
                        "travel_time_min": 0,
                        "visit_duration_min": 60,
                    }
                ],
            }
        ],
    }


async def test_owner_get_returns_run(client, db_session) -> None:
    run, _ = await PlannerRunService(db_session).resolve(
        session_id="sess-get",
        user_id=None,
        idempotency_key="get-key",
        input_hash="d" * 64,
    )
    response = await client.get(
        f"/api/v1/planner/runs/{run.id}",
        cookies={"wandr_session": "sess-get"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["run_id"] == str(run.id)
    assert data["status"] == "planning"
    assert data["failure_code"] is None
    assert data["trip_id"] is None
    assert "idempotency_key" not in data
    assert "input_hash" not in data
    assert "session_id" not in data


async def test_wrong_session_is_403(client, db_session) -> None:
    run, _ = await PlannerRunService(db_session).resolve(
        session_id="sess-owner",
        user_id=None,
        idempotency_key="own-key",
        input_hash="e" * 64,
    )
    response = await client.get(
        f"/api/v1/planner/runs/{run.id}",
        cookies={"wandr_session": "someone-else"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


async def test_unknown_run_is_404(client) -> None:
    response = await client.get(f"/api/v1/planner/runs/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_committed_trip_id_is_visible_without_sse(client, db_session) -> None:
    state = await _state(db_session)
    run, _ = await PlannerRunService(db_session).resolve(
        session_id="sess-saved",
        user_id=None,
        idempotency_key="saved-key",
        input_hash="f" * 64,
    )
    trip = await TripService(db_session).save_from_state(
        state,
        user_id=None,
        session_id="sess-saved",
        run_id=run.id,
    )
    assert trip is not None
    response = await client.get(
        f"/api/v1/planner/runs/{run.id}",
        cookies={"wandr_session": "sess-saved"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trip_id"] == str(trip.id)
    assert data["status"] == "completed"
