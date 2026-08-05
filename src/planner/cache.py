"""Planner result cache — MVP key + CacheBackend get/set + cache-hit replay."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from typing import Any

import structlog

from src.config import get_settings
from src.core.cache import get_cache_backend
from src.planner.schemas import PlanRequest

log = structlog.get_logger()

_KEY_PREFIX = "wandr:planner:v1:"
_WHITESPACE_RE = re.compile(r"\s+")

# Fields sufficient for SSE display + TripService.save_from_state
_CACHEABLE_FIELDS = (
    "destination_id",
    "destination_name",
    "schedule",
    "itinerary",
    "interests",
    "budget",
    "include_offbeat",
    "include_trekking",
    "days",
    "plan_complete",
    "abort_triggered",
    "base_lat",
    "base_lng",
    "raw_input",
    "warnings",
)


def normalize_raw_input(raw_input: str) -> str:
    """Strip + collapse internal whitespace for MVP cache key."""
    return _WHITESPACE_RE.sub(" ", (raw_input or "").strip())


def build_planner_cache_key(
    body: PlanRequest,
    base_lat: float,
    base_lng: float,
) -> str:
    """
    Locked MVP key (step6 v2):
      sha256(f"{destination_id}:{sha256(normalized_raw_input)}:{days_or_0}:"
             f"{round(base_lat,3)}:{round(base_lng,3)}")
    """
    normalized = normalize_raw_input(body.raw_input)
    raw_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    days_or_0 = body.days if body.days is not None else 0
    material = (
        f"{body.destination_id}:{raw_hash}:{days_or_0}:"
        f"{round(base_lat, 3)}:{round(base_lng, 3)}"
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"{_KEY_PREFIX}{digest}"


def _cacheable_subset(state: dict[str, Any]) -> dict[str, Any] | None:
    """Build lean JSON-serializable subset; None if not cache-worthy."""
    if not state.get("plan_complete") or state.get("abort_triggered"):
        return None
    schedule = state.get("schedule") or []
    if not isinstance(schedule, list) or not schedule:
        return None
    subset = {k: state.get(k) for k in _CACHEABLE_FIELDS if k in state}
    subset["plan_complete"] = True
    subset["abort_triggered"] = False
    if "destination_id" not in subset and state.get("destination_id") is not None:
        subset["destination_id"] = state["destination_id"]
    subset["schedule"] = schedule
    return subset


async def maybe_get_cached_state(
    body: PlanRequest,
    base_lat: float,
    base_lng: float,
) -> dict[str, Any] | None:
    """
    Lookup cached TravelState subset for PlanRequest + resolved base coords.
    Backend errors → miss (None). Never raises.
    """
    key = build_planner_cache_key(body, base_lat, base_lng)
    try:
        raw = await get_cache_backend().get(key)
    except Exception as exc:
        log.warning("planner_cache.get_error", error=str(exc))
        return None
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        log.warning("planner_cache.decode_error", error=str(exc))
        return None
    if not isinstance(data, dict):
        return None
    return data


async def maybe_set_cached_state(
    body: PlanRequest,
    base_lat: float,
    base_lng: float,
    state: dict[str, Any],
) -> None:
    """Best-effort cache write after a successful fresh generation. Never raises."""
    subset = _cacheable_subset(state)
    if subset is None:
        return
    key = build_planner_cache_key(body, base_lat, base_lng)
    ttl = get_settings().PLANNER_CACHE_TTL_SECONDS
    try:
        payload = json.dumps(subset, default=str)
        await get_cache_backend().set(key, payload, ttl)
    except Exception as exc:
        log.warning("planner_cache.set_error", error=str(exc))


async def _replay_cached(
    cached_state: dict[str, Any],
    on_event: Callable[[str, dict], None],
) -> dict[str, Any]:
    """
    Emit preferences_done / phase_changed / itinerary_done from cache without the tool loop.
    Returns a final_state dict shaped for TripService.save_from_state.
    Does NOT emit tool_started / tool_done.
    """
    prefs = {
        "interests": cached_state.get("interests") or [],
        "budget": cached_state.get("budget"),
        "days": cached_state.get("days"),
        "include_offbeat": cached_state.get("include_offbeat"),
        "include_trekking": cached_state.get("include_trekking"),
    }
    on_event("preferences_done", prefs)
    on_event("phase_changed", {"phase": "WRAP_UP", "from_cache": True})

    itinerary = cached_state.get("itinerary") or {}
    on_event(
        "itinerary_done",
        {
            "itinerary": itinerary,
            "from_cache": True,
            "days": len(cached_state.get("schedule") or []),
        },
    )

    # Return a copy so callers can mutate safely; ensure save flags
    final_state = dict(cached_state)
    final_state["plan_complete"] = True
    final_state["abort_triggered"] = False
    return final_state
