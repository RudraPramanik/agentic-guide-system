"""Unit tests for cold-path SSE terminal resolution."""

from __future__ import annotations

from src.planner.emit_terminals import (
    emit_terminal_from_state,
    resolve_terminal_from_state,
    schedule_usable,
)


def test_schedule_usable_requires_stops() -> None:
    assert schedule_usable([]) is False
    assert schedule_usable([{"day": 1, "stops": []}]) is False
    assert schedule_usable([{"day": 1, "stops": [{"place_id": "p1"}]}]) is True


def test_already_emitted_error_skips_second_terminal() -> None:
    state = {
        "plan_complete": True,
        "schedule": [{"day": 1, "stops": [{"place_id": "p1"}]}],
    }
    assert (
        resolve_terminal_from_state(state, already_emitted_error=True) is None
    )


def test_clarification_takes_precedence_over_schedule() -> None:
    state = {
        "needs_clarification": True,
        "clarification_question": "How many days?",
        "plan_complete": True,
        "schedule": [{"day": 1, "stops": [{"place_id": "p1"}]}],
    }
    event, data = resolve_terminal_from_state(state)  # type: ignore[misc]
    assert event == "clarification_needed"
    assert data["question"] == "How many days?"


def test_clarification_default_question() -> None:
    state = {"needs_clarification": True, "clarification_question": "  "}
    event, data = resolve_terminal_from_state(state)  # type: ignore[misc]
    assert event == "clarification_needed"
    assert "clarify" in data["question"].lower()


def test_success_itinerary_done_payload() -> None:
    state = {
        "plan_complete": True,
        "days": 2,
        "schedule": [{"day": 1, "stops": [{"place_id": "p1"}]}],
        "itinerary": {"days": [{"day": 1, "title": "Explore"}]},
    }
    event, data = resolve_terminal_from_state(state)  # type: ignore[misc]
    assert event == "itinerary_done"
    assert data["days"] == 2
    assert data["itinerary"]["days"][0]["title"] == "Explore"


def test_abort_when_incomplete() -> None:
    state = {"plan_complete": False, "schedule": []}
    event, data = resolve_terminal_from_state(state)  # type: ignore[misc]
    assert event == "error"
    assert data["code"] == "generation_aborted"


def test_emit_terminal_invokes_on_event() -> None:
    events: list[tuple[str, dict]] = []

    def _emit(event: str, data: dict, state_snapshot=None) -> None:
        events.append((event, data))

    state = {
        "plan_complete": True,
        "schedule": [{"day": 1, "stops": [{"place_id": "p1"}]}],
        "itinerary": {},
        "days": 1,
    }
    resolved = emit_terminal_from_state(state, _emit)
    assert resolved is not None
    assert events == [("itinerary_done", {"itinerary": {}, "days": 1})]


def test_emit_skipped_when_already_emitted_error() -> None:
    events: list[tuple[str, dict]] = []

    def _emit(event: str, data: dict, state_snapshot=None) -> None:
        events.append((event, data))

    emit_terminal_from_state(
        {"plan_complete": True, "schedule": [{"day": 1, "stops": [{"place_id": "x"}]}]},
        _emit,
        already_emitted_error=True,
    )
    assert events == []
