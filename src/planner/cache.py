"""Planner result cache helpers.

P6.2: always-miss stub so the SSE router shape is stable.
P6.4: wire CacheBackend + MVP key + _replay_cached that still feeds save_from_state.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.planner.schemas import PlanRequest


async def maybe_get_cached_state(
    body: PlanRequest,
    base_lat: float,
    base_lng: float,
) -> dict[str, Any] | None:
    """
    Lookup cached TravelState subset for PlanRequest + resolved base coords.

    P6.2 always returns None (miss). P6.4 implements the locked MVP key + backend.
    """
    _ = (body, base_lat, base_lng)
    return None


async def _replay_cached(
    cached_state: dict[str, Any],
    on_event: Callable[[str, dict], None],
) -> dict[str, Any]:
    """
    Emit preferences_done / phase_changed / itinerary_done from cache without the tool loop.
    Returns a final_state dict shaped for TripService.save_from_state.

    Unused until P6.4 — raise so accidental calls are obvious.
    """
    _ = (cached_state, on_event)
    raise NotImplementedError("_replay_cached lands in P6.4 with CacheBackend")
