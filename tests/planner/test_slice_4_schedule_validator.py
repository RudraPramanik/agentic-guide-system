"""Tool wiring for allocator, schedule V2, and validator shadow/enforce."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.planner.tools import build_route as build_route_mod
from src.planner.tools import build_schedule as build_schedule_mod
from src.planner.tools import validate_itinerary as validate_mod
from src.planner.tools.schemas import BuildRouteIn, BuildScheduleIn, ValidateItineraryIn
from src.travel_engine.day_allocator import allocate_days
from src.travel_engine.schedule_builder import build_day_schedule
from tests.travel_engine.fake_routing import FakeRoutingProvider


def _stop(name: str, start: str) -> dict:
    return {
        "place_id": str(uuid4()),
        "name": name,
        "lat": 27.03,
        "lng": 88.26,
        "category": "attraction",
        "suggested_start_time": start,
        "visit_duration_min": 30,
        "score": 1.0,
        "enriched_tags": ["photography"],
        "evidence_count": 1,
        "opening_hours_status": "verified",
        "opening_open": "08:00",
        "opening_close": "18:00",
    }


@pytest.mark.asyncio
async def test_build_route_flag_off_allocates_with_mode_off() -> None:
    place_id = str(uuid4())
    state = {
        "ranked_pois": [
            {
                "place": {
                    "id": place_id,
                    "name": "Museum",
                    "category": "museum",
                    "enriched_tags": ["cultural"],
                    "lat": 27.04,
                    "lng": 88.26,
                },
                "score": 1.0,
                "score_breakdown": {},
            }
        ],
        "preferences": {"interests": ["cultural"], "days": 1},
        "base_lat": 27.03,
        "base_lng": 88.26,
    }
    ctx = SimpleNamespace(
        routing=FakeRoutingProvider(default_duration_min=10, default_distance_km=1.0),
        base_lat=27.03,
        base_lng=88.26,
    )
    settings = SimpleNamespace(TRAVEL_ENGINE_V2_ENABLED=False)
    with (
        patch.object(build_route_mod, "get_settings", return_value=settings),
        patch.object(build_route_mod, "allocate_days", wraps=allocate_days) as spy,
    ):
        result = await build_route_mod.run(BuildRouteIn(), ctx=ctx, state=state)
    assert result.ok is True
    assert spy.call_args.kwargs["v2_enabled"] is False


@pytest.mark.asyncio
async def test_build_schedule_flag_on_uses_v2_timing() -> None:
    place_id = str(uuid4())
    state = {
        "route": [
            {
                "ordered": [
                    {
                        "place": {
                            "id": place_id,
                            "name": "Museum",
                            "category": "museum",
                            "enriched_tags": [],
                            "lat": 27.04,
                            "lng": 88.26,
                        },
                        "score": 1.0,
                    }
                ],
                "legs": [
                    {
                        "from_place_id": "00000000-0000-0000-0000-000000000000",
                        "to_place_id": place_id,
                        "duration_min": 10,
                        "distance_km": 1.0,
                        "used_fallback": False,
                    }
                ],
                "total_travel_min": 10,
                "leg_polylines": [None],
                "day_polyline": None,
            }
        ]
    }
    settings = SimpleNamespace(TRAVEL_ENGINE_V2_ENABLED=True)
    with (
        patch.object(build_schedule_mod, "get_settings", return_value=settings),
        patch.object(
            build_schedule_mod, "build_day_schedule", wraps=build_day_schedule
        ) as spy,
    ):
        result = await build_schedule_mod.run(BuildScheduleIn(), ctx=None, state=state)
    assert result.ok is True
    assert spy.call_args.kwargs["v2_enabled"] is True
    assert spy.call_args.kwargs.get("preserve_order", False) is False


@pytest.mark.asyncio
async def test_validate_shadow_keeps_ok_when_v6_passes() -> None:
    state = {
        "schedule": [
            {
                "stops": [_stop("Later", "10:00"), _stop("Earlier", "09:00")],
                "total_travel_min": 10,
            }
        ],
        "route": [],
    }
    settings = SimpleNamespace(VALIDATOR_V2_ENFORCE=False)
    with patch.object(validate_mod, "get_settings", return_value=settings):
        result = await validate_mod.run(ValidateItineraryIn(), state=state)
    assert result.ok is True
    assert result.data["validation_result"]["passed"] is True
    assert result.data["last_validate_ok"] is True
    codes = {item["code"] for item in result.data["v2_findings"]}
    assert "NON_CHRONOLOGICAL_SCHEDULE" in codes


@pytest.mark.asyncio
async def test_validate_enforce_blocks_critical_finding() -> None:
    state = {
        "schedule": [
            {
                "stops": [_stop("Later", "10:00"), _stop("Earlier", "09:00")],
                "total_travel_min": 10,
            }
        ],
        "route": [],
    }
    settings = SimpleNamespace(VALIDATOR_V2_ENFORCE=True)
    with patch.object(validate_mod, "get_settings", return_value=settings):
        result = await validate_mod.run(ValidateItineraryIn(), state=state)
    assert result.ok is False
    assert result.data["validation_result"]["passed"] is True
    assert result.data["last_validate_ok"] is False
