"""Flag-on generate idempotency. Selected by ``-k idempotent``."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func, select

from src.config import get_settings
from src.core.middleware.rate_limit import InMemoryRateLimiter, _reset_rate_limiter_for_tests
from src.destinations.models import Destination
from src.places.models import Place
from src.planner.runs.models import PlannerRun
from src.planner.runs.service import PlannerRunService
from src.trips.models import Trip


@pytest.fixture(autouse=True)
def _fresh_rate_limiter():
    _reset_rate_limiter_for_tests(InMemoryRateLimiter())
    yield
    _reset_rate_limiter_for_tests(None)


def _enable(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "RUN_TRACKING_ENABLED", True)


async def _ready(db_session) -> tuple[Destination, Place]:
    dest = Destination(
        name="Run Dest",
        country="IN",
        display_name="Run Dest",
        osm_place_id=f"relation/run-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=50,
    )
    db_session.add(dest)
    await db_session.flush()
    place = Place(
        osm_id=f"node/run-{uuid.uuid4().hex[:8]}",
        name="Run Stop",
        category="attraction",
        tags={},
        location=from_shape(Point(88.263, 27.041), srid=4326),
        destination_id=dest.id,
    )
    db_session.add(place)
    await db_session.flush()
    return dest, place


def _saved_state(dest: Destination, place: Place) -> dict:
    return {
        "destination_id": str(dest.id),
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
                        "leg_polyline": None,
                    }
                ],
                "total_distance_km": 0.0,
                "total_travel_min": 0,
                "day_polyline": None,
            }
        ],
        "interests": ["nature"],
        "budget": "mid",
        "include_offbeat": False,
        "include_trekking": False,
        "plan_complete": True,
        "abort_triggered": False,
    }


def _frames(text: str) -> list[tuple[str, dict]]:
    frames: list[tuple[str, dict]] = []
    event: str | None = None
    for line in text.splitlines():
        if line.startswith("event: "):
            event = line.removeprefix("event: ")
        elif line.startswith("data: ") and event is not None:
            frames.append((event, json.loads(line.removeprefix("data: "))))
            event = None
    return frames


def _payload(dest: Destination, raw: str) -> dict:
    return {"destination_id": str(dest.id), "raw_input": raw}


@pytest.mark.asyncio
async def test_idempotent_double_submit_creates_one_trip(client, db_session, monkeypatch) -> None:
    _enable(monkeypatch)
    dest, place = await _ready(db_session)
    state = _saved_state(dest, place)

    async def _fake_generate(**kwargs):
        kwargs["on_event"]("itinerary_done", {"days": []})
        return state

    with patch(
        "src.planner.router.PlannerService.generate",
        new=AsyncMock(side_effect=_fake_generate),
    ) as mock_generate:
        first = await client.post(
            "/api/v1/planner/generate",
            json=_payload(dest, "tea gardens"),
            headers={"Idempotency-Key": "submit-1"},
        )
        second = await client.post(
            "/api/v1/planner/generate",
            json=_payload(dest, "tea gardens"),
            headers={"Idempotency-Key": "submit-1"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    first_done = [data for event, data in _frames(first.text) if event == "itinerary_done"]
    second_done = [data for event, data in _frames(second.text) if event == "itinerary_done"]
    assert len(first_done) == 1
    assert len(second_done) == 1
    assert first_done[0]["trip_id"] == second_done[0]["trip_id"]
    assert first_done[0]["run_id"] == second_done[0]["run_id"]
    assert mock_generate.await_count == 1
    trips = (await db_session.execute(select(func.count()).select_from(Trip))).scalar_one()
    assert trips == 1


@pytest.mark.asyncio
async def test_idempotent_in_progress_does_not_generate(client, db_session, monkeypatch) -> None:
    _enable(monkeypatch)
    dest, _place = await _ready(db_session)
    run, created = await PlannerRunService(db_session).resolve(
        session_id="sess-busy",
        user_id=None,
        idempotency_key="busy-key",
        input_hash="c" * 64,
    )
    assert created is True

    with patch(
        "src.planner.router.PlannerService.generate",
        new_callable=AsyncMock,
    ) as mock_generate:
        response = await client.post(
            "/api/v1/planner/generate",
            json=_payload(dest, "tea gardens"),
            headers={"Idempotency-Key": "busy-key"},
            cookies={"wandr_session": "sess-busy"},
        )

    assert response.status_code == 200
    frames = _frames(response.text)
    assert frames == [("error", {"code": "run_in_progress", "run_id": str(run.id)})]
    mock_generate.assert_not_called()


@pytest.mark.asyncio
async def test_idempotent_same_key_different_body_reuses_run(
    client, db_session, monkeypatch
) -> None:
    _enable(monkeypatch)
    dest, place = await _ready(db_session)
    state = _saved_state(dest, place)

    async def _fake_generate(**kwargs):
        kwargs["on_event"]("itinerary_done", {})
        return state

    with patch(
        "src.planner.router.PlannerService.generate",
        new=AsyncMock(side_effect=_fake_generate),
    ) as mock_generate:
        first = await client.post(
            "/api/v1/planner/generate",
            json=_payload(dest, "tea gardens"),
            headers={"Idempotency-Key": "same-key"},
        )
        second = await client.post(
            "/api/v1/planner/generate",
            json=_payload(dest, "coffee shops"),
            headers={"Idempotency-Key": "same-key"},
        )

    assert mock_generate.await_count == 1
    first_id = _frames(first.text)[-1][1]["run_id"]
    second_id = _frames(second.text)[-1][1]["run_id"]
    assert first_id == second_id
    rows = (await db_session.execute(select(PlannerRun))).scalars().all()
    assert len(rows) == 1
    assert rows[0].input_hash != ""


@pytest.mark.asyncio
async def test_idempotent_new_key_cache_hit_saves_another_trip(
    client, db_session, monkeypatch
) -> None:
    _enable(monkeypatch)
    dest, place = await _ready(db_session)
    state = _saved_state(dest, place)

    with (
        patch(
            "src.planner.router.maybe_get_cached_state",
            new=AsyncMock(return_value=state),
        ),
        patch(
            "src.planner.router.PlannerService.generate",
            new_callable=AsyncMock,
        ) as mock_generate,
    ):
        first = await client.post(
            "/api/v1/planner/generate",
            json=_payload(dest, "cached trip"),
            headers={"Idempotency-Key": "cache-a"},
        )
        second = await client.post(
            "/api/v1/planner/generate",
            json=_payload(dest, "cached trip"),
            headers={"Idempotency-Key": "cache-b"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    first_trip = [d for e, d in _frames(first.text) if e == "itinerary_done"][0]["trip_id"]
    second_trip = [d for e, d in _frames(second.text) if e == "itinerary_done"][0]["trip_id"]
    assert first_trip != second_trip
    mock_generate.assert_not_called()


@pytest.mark.asyncio
async def test_idempotent_flag_off_writes_no_run(client, db_session, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "RUN_TRACKING_ENABLED", False)
    dest, _place = await _ready(db_session)

    async def _fake_generate(**kwargs):
        kwargs["on_event"]("phase_changed", {"phase": "discover"})
        kwargs["on_event"]("itinerary_done", {"days": []})
        return {
            "destination_id": str(dest.id),
            "schedule": [],
            "plan_complete": False,
            "abort_triggered": False,
        }

    with patch(
        "src.planner.router.PlannerService.generate",
        new=AsyncMock(side_effect=_fake_generate),
    ):
        response = await client.post(
            "/api/v1/planner/generate",
            json=_payload(dest, "weekend"),
            headers={"Idempotency-Key": "ignored"},
        )

    assert response.status_code == 200
    assert "run_id" not in response.text
    count = (
        await db_session.execute(select(func.count()).select_from(PlannerRun))
    ).scalar_one()
    assert count == 0
