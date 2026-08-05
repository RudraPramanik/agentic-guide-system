"""P6.2 planner generate SSE — floor check and route surface."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from src.destinations.models import Destination


@pytest.mark.asyncio
async def test_generate_floor_place_count_zero_returns_409(client, db_session) -> None:
    dest = Destination(
        name="Empty Dest",
        country="IN",
        display_name="Empty Dest",
        osm_place_id=f"relation/empty-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=0,
    )
    db_session.add(dest)
    await db_session.flush()

    with patch(
        "src.planner.router.PlannerService.generate",
        new_callable=AsyncMock,
    ) as mock_generate:
        response = await client.post(
            "/api/v1/planner/generate",
            json={
                "destination_id": str(dest.id),
                "raw_input": "3 day trip",
            },
        )

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "destination_not_ready"
    assert body["details"]["place_count"] == 0
    mock_generate.assert_not_called()


@pytest.mark.asyncio
async def test_generate_route_registered_headers_on_stream(client, db_session) -> None:
    """Ready destination streams SSE; proxy headers present; session cookie set."""
    dest = Destination(
        name="Ready Dest",
        country="IN",
        display_name="Ready Dest",
        osm_place_id=f"relation/ready-gen-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=50,
    )
    db_session.add(dest)
    await db_session.flush()

    async def _fake_generate(**kwargs):
        on_event = kwargs["on_event"]
        on_event("phase_changed", {"phase": "discover"})
        on_event("itinerary_done", {"days": []})
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
            json={
                "destination_id": str(dest.id),
                "raw_input": "weekend getaway",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("cache-control") == "no-cache"
    assert response.headers.get("x-accel-buffering") == "no"
    assert "wandr_session" in response.cookies
    text = response.text
    assert "event: phase_changed" in text
    assert "event: itinerary_done" in text
    # Exactly one terminal event name occurrence for itinerary_done
    assert text.count("event: itinerary_done") == 1


@pytest.mark.asyncio
async def test_generate_single_terminal_when_spurious_second(client, db_session) -> None:
    """Only one terminal SSE frame reaches the client even if service emits two."""
    dest = Destination(
        name="Terminal Dest",
        country="IN",
        display_name="Terminal Dest",
        osm_place_id=f"relation/term-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=50,
    )
    db_session.add(dest)
    await db_session.flush()

    async def _fake_generate(**kwargs):
        on_event = kwargs["on_event"]
        on_event("itinerary_done", {"ok": True})
        on_event("error", {"message": "spurious"})
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
            json={"destination_id": str(dest.id), "raw_input": "trip"},
        )

    assert response.status_code == 200
    text = response.text
    terminal_count = text.count("event: itinerary_done") + text.count("event: error")
    assert terminal_count == 1


@pytest.mark.asyncio
async def test_cache_hit_skips_tools_still_saves_new_trip(client, db_session) -> None:
    """Cache hit: no tool_* events, no PlannerService.generate, still new trip_id."""
    from geoalchemy2.shape import from_shape
    from shapely.geometry import Point

    from src.places.models import Place

    dest = Destination(
        name="Cache Dest",
        country="IN",
        display_name="Cache Dest",
        osm_place_id=f"relation/cache-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=50,
    )
    db_session.add(dest)
    await db_session.flush()

    place = Place(
        osm_id=f"node/cache-{uuid.uuid4().hex[:8]}",
        name="Cached Stop",
        category="attraction",
        tags={},
        location=from_shape(Point(88.263, 27.041), srid=4326),
        destination_id=dest.id,
    )
    db_session.add(place)
    await db_session.flush()

    cached_state = {
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
        "itinerary": {"title": "From cache"},
        "interests": ["nature"],
        "budget": "mid",
        "include_offbeat": False,
        "include_trekking": False,
        "days": 1,
        "plan_complete": True,
        "abort_triggered": False,
    }

    with (
        patch(
            "src.planner.router.maybe_get_cached_state",
            new=AsyncMock(return_value=cached_state),
        ),
        patch(
            "src.planner.router.PlannerService.generate",
            new_callable=AsyncMock,
        ) as mock_generate,
    ):
        response = await client.post(
            "/api/v1/planner/generate",
            json={
                "destination_id": str(dest.id),
                "raw_input": "cached trip",
            },
        )

    assert response.status_code == 200
    text = response.text
    assert "event: tool_started" not in text
    assert "event: tool_done" not in text
    assert "event: itinerary_done" in text
    assert "trip_id" in text
    mock_generate.assert_not_called()

    # Second identical cache hit → different trip_id
    with (
        patch(
            "src.planner.router.maybe_get_cached_state",
            new=AsyncMock(return_value=cached_state),
        ),
        patch(
            "src.planner.router.PlannerService.generate",
            new_callable=AsyncMock,
        ),
    ):
        response2 = await client.post(
            "/api/v1/planner/generate",
            json={
                "destination_id": str(dest.id),
                "raw_input": "cached trip",
            },
        )

    import json as _json
    import re

    def _trip_id(body: str) -> str:
        m = re.search(r"event: itinerary_done\ndata: (.+)\n", body)
        assert m
        return _json.loads(m.group(1))["trip_id"]

    assert _trip_id(text) != _trip_id(response2.text)


@pytest.mark.asyncio
async def test_disconnect_cancels_background_task(client, db_session) -> None:
    """Background generate is cancelled once the client is disconnected."""
    import asyncio

    from starlette.requests import Request

    dest = Destination(
        name="Disconnect Dest",
        country="IN",
        display_name="Disconnect Dest",
        osm_place_id=f"relation/disc-{uuid.uuid4().hex[:8]}",
        lat=27.041,
        lng=88.263,
        place_count=50,
    )
    db_session.add(dest)
    await db_session.flush()

    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def _slow_generate(**kwargs):
        started.set()
        try:
            await asyncio.sleep(120)
        except asyncio.CancelledError:
            cancelled.set()
            raise
        return {}

    async def _disconnect_after_start(_self) -> bool:
        # Allow the generate task to begin, then report disconnected
        return started.is_set()

    with (
        patch(
            "src.planner.router.PlannerService.generate",
            new=AsyncMock(side_effect=_slow_generate),
        ),
        patch.object(Request, "is_disconnected", _disconnect_after_start),
    ):
        response = await client.post(
            "/api/v1/planner/generate",
            json={
                "destination_id": str(dest.id),
                "raw_input": "slow",
            },
        )

    assert response.status_code == 200
    assert cancelled.is_set()
