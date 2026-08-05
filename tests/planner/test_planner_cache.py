"""P6.4 planner cache key / get / set / replay."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.core.cache.backends import InMemoryCacheBackend, _reset_cache_backend_for_tests
from src.planner.cache import (
    _replay_cached,
    build_planner_cache_key,
    maybe_get_cached_state,
    maybe_set_cached_state,
    normalize_raw_input,
)
from src.planner.schemas import PlanRequest


@pytest.fixture(autouse=True)
def _mem_cache():
    backend = InMemoryCacheBackend()
    _reset_cache_backend_for_tests(backend)
    yield backend
    _reset_cache_backend_for_tests(None)


def test_normalize_and_key_whitespace_rounding() -> None:
    dest = uuid4()
    a = PlanRequest(destination_id=dest, raw_input="  hello   world  ")
    b = PlanRequest(destination_id=dest, raw_input="hello world")
    assert normalize_raw_input(a.raw_input) == "hello world"
    assert build_planner_cache_key(a, 27.0414, 88.2631) == build_planner_cache_key(
        b, 27.0412, 88.2634
    )


def test_key_differs_on_days() -> None:
    dest = uuid4()
    a = PlanRequest(destination_id=dest, raw_input="trip", days=None)
    b = PlanRequest(destination_id=dest, raw_input="trip", days=3)
    assert build_planner_cache_key(a, 1.0, 2.0) != build_planner_cache_key(b, 1.0, 2.0)


@pytest.mark.asyncio
async def test_maybe_get_set_roundtrip() -> None:
    dest = uuid4()
    body = PlanRequest(destination_id=dest, raw_input="3 day trek")
    state = {
        "destination_id": str(dest),
        "schedule": [{"day": 1, "stops": [{"place_id": str(uuid4()), "order": 0}]}],
        "itinerary": {"title": "Trek"},
        "interests": ["nature"],
        "budget": "mid",
        "plan_complete": True,
        "abort_triggered": False,
        "days": 3,
    }
    assert await maybe_get_cached_state(body, 27.0, 88.0) is None
    await maybe_set_cached_state(body, 27.0, 88.0, state)
    hit = await maybe_get_cached_state(body, 27.0, 88.0)
    assert hit is not None
    assert hit["plan_complete"] is True
    assert hit["itinerary"]["title"] == "Trek"


@pytest.mark.asyncio
async def test_set_skips_incomplete_state() -> None:
    dest = uuid4()
    body = PlanRequest(destination_id=dest, raw_input="x")
    await maybe_set_cached_state(
        body,
        1.0,
        2.0,
        {"plan_complete": False, "abort_triggered": False, "schedule": []},
    )
    assert await maybe_get_cached_state(body, 1.0, 2.0) is None


@pytest.mark.asyncio
async def test_replay_cached_emits_no_tool_events() -> None:
    events: list[tuple[str, dict]] = []

    def on_event(event: str, data: dict) -> None:
        events.append((event, data))

    state = {
        "destination_id": str(uuid4()),
        "schedule": [{"day": 1, "stops": []}],
        "itinerary": {"title": "Cached"},
        "interests": ["food"],
        "budget": "low",
        "days": 1,
        "plan_complete": True,
        "abort_triggered": False,
    }
    final = await _replay_cached(state, on_event)
    names = [e for e, _ in events]
    assert "tool_started" not in names
    assert "tool_done" not in names
    assert "preferences_done" in names
    assert "itinerary_done" in names
    assert final["plan_complete"] is True
    assert final["itinerary"]["title"] == "Cached"


@pytest.mark.asyncio
async def test_get_tolerates_backend_raise(monkeypatch) -> None:
    class Boom:
        async def get(self, key: str):
            raise RuntimeError("boom")

        async def set(self, key: str, value: str, ttl_seconds: int) -> None:
            raise RuntimeError("boom")

    _reset_cache_backend_for_tests(Boom())  # type: ignore[arg-type]
    body = PlanRequest(destination_id=uuid4(), raw_input="x")
    assert await maybe_get_cached_state(body, 1.0, 2.0) is None
    await maybe_set_cached_state(
        body,
        1.0,
        2.0,
        {
            "destination_id": str(body.destination_id),
            "schedule": [{"day": 1, "stops": [{"x": 1}]}],
            "plan_complete": True,
            "abort_triggered": False,
        },
    )
