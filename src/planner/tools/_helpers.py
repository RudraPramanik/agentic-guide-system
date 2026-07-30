"""Shared helpers for planner tools — state view + serialization (no I/O)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from geoalchemy2.shape import to_shape

from src.places.models import Place
from src.travel_engine.place_selector import (
    PlaceCandidate,
    ScoredPlace,
    TripPreferences,
)


def resolve_state(ctx: Any, state: Any = None) -> Any:
    """Prefer explicit state arg; else ctx.state if present."""
    if state is not None:
        return state
    if ctx is not None and hasattr(ctx, "state"):
        return getattr(ctx, "state")
    return None


def state_get(state: Any, key: str, default: Any = None) -> Any:
    if state is None:
        return default
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def place_to_candidate(place: Place) -> PlaceCandidate:
    point = to_shape(place.location)
    tags = place.enriched_tags if isinstance(place.enriched_tags, list) else []
    return PlaceCandidate(
        id=place.id,
        name=place.name,
        category=place.category,
        enriched_tags=list(tags),
        lat=float(point.y),
        lng=float(point.x),
    )


def candidate_to_dict(c: PlaceCandidate) -> dict:
    return c.model_dump(mode="json")


def scored_to_dict(s: ScoredPlace) -> dict:
    return s.model_dump(mode="json")


def dict_to_scored(d: dict) -> ScoredPlace:
    return ScoredPlace.model_validate(d)


def dict_to_candidate(d: dict) -> PlaceCandidate:
    return PlaceCandidate.model_validate(d)


def preferences_from_state(state: Any) -> TripPreferences:
    prefs = state_get(state, "preferences")
    if isinstance(prefs, TripPreferences):
        return prefs
    if isinstance(prefs, dict):
        return TripPreferences.model_validate(prefs)
    interests = state_get(state, "interests") or []
    if isinstance(interests, str):
        interests = [interests]
    days = state_get(state, "days", 3) or 3
    budget = state_get(state, "budget")
    raw = state_get(state, "raw_input") or ""
    if not interests and raw:
        interests = [t for t in str(raw).lower().split() if len(t) > 2]
    return TripPreferences(
        interests=list(interests) if interests else [],
        budget=budget,
        days=int(days),
    )


def search_query_from_state(state: Any, override: str | None = None) -> str:
    if override:
        return override
    prefs = preferences_from_state(state)
    if prefs.interests:
        return " ".join(prefs.interests)
    raw = state_get(state, "raw_input")
    if raw:
        return str(raw)
    return "attractions"


def as_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
