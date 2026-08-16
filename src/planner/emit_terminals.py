"""Map final TravelState to a single SSE terminal event (cold generate path)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

EmitFn = Callable[..., None]

_DEFAULT_CLARIFICATION = "Could you clarify your trip preferences?"


def schedule_usable(schedule: Any) -> bool:
    """True when schedule has at least one day with stops (mirrors TripService)."""
    if not isinstance(schedule, list) or not schedule:
        return False
    for day in schedule:
        if not isinstance(day, dict):
            continue
        stops = day.get("stops") or []
        if isinstance(stops, list) and len(stops) > 0:
            return True
    return False


def resolve_terminal_from_state(
    state: dict[str, Any],
    *,
    already_emitted_error: bool = False,
) -> tuple[str, dict[str, Any]] | None:
    """
    Locked precedence → one terminal, or None if an error terminal was already emitted.

    1. already_emitted_error → None (no second terminal)
    2. needs_clarification → clarification_needed
    3. plan_complete + usable schedule → itinerary_done
    4. else → error generation_aborted
    """
    if already_emitted_error:
        return None

    if state.get("needs_clarification"):
        question = state.get("clarification_question")
        if not isinstance(question, str) or not question.strip():
            question = _DEFAULT_CLARIFICATION
        return (
            "clarification_needed",
            {"question": question.strip()},
        )

    schedule = state.get("schedule") or []
    if state.get("plan_complete") and schedule_usable(schedule):
        itinerary = state.get("itinerary")
        if not isinstance(itinerary, dict):
            itinerary = {}
        days = state.get("days")
        if not isinstance(days, int) or days <= 0:
            days = len(schedule) if isinstance(schedule, list) else 0
        return (
            "itinerary_done",
            {
                "itinerary": itinerary,
                "days": days,
            },
        )

    return ("error", {"code": "generation_aborted"})


def emit_terminal_from_state(
    state: dict[str, Any],
    emit: EmitFn | None,
    *,
    already_emitted_error: bool = False,
) -> tuple[str, dict[str, Any]] | None:
    """Resolve and emit one terminal via ``emit(event, data, state_snapshot=...)``."""
    resolved = resolve_terminal_from_state(
        state, already_emitted_error=already_emitted_error
    )
    if resolved is None:
        return None
    event, data = resolved
    if callable(emit):
        emit(event, data, state_snapshot=dict(state))
    return resolved
