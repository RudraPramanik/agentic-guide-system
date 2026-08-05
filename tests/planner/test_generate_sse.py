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
