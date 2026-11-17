"""Pure generate outcome mapping."""

from __future__ import annotations

from src.core.exceptions import WandrLLMError
from src.planner.runs.models import RunStatus
from src.planner.runs.outcomes import map_generate_outcome


def _map(**kwargs):
    defaults = {
        "disconnected": False,
        "task_error": None,
        "state": None,
        "terminal_event": None,
        "terminal_data": None,
        "saved": False,
    }
    defaults.update(kwargs)
    return map_generate_outcome(**defaults)


def test_timeout_is_timed_out() -> None:
    outcome = _map(terminal_event="error", terminal_data={"code": "generation_timeout"})
    assert outcome.status is RunStatus.TIMED_OUT
    assert outcome.failure_code == "generation_timeout"


def test_recursion_is_failed() -> None:
    outcome = _map(
        state={"errors": ["graph_recursion_limit"]},
        terminal_event="error",
        terminal_data={"code": "graph_recursion_limit"},
    )
    assert outcome.status is RunStatus.FAILED
    assert outcome.failure_code == "graph_recursion_limit"


def test_llm_error_is_unavailable() -> None:
    outcome = _map(task_error=WandrLLMError("down", "llm down"))
    assert outcome.status is RunStatus.FAILED
    assert outcome.failure_code == "llm_unavailable"


def test_clarification_is_failed_with_code() -> None:
    outcome = _map(
        state={"needs_clarification": True},
        terminal_event="clarification_needed",
        terminal_data={"question": "When?"},
    )
    assert outcome.status is RunStatus.FAILED
    assert outcome.failure_code == "needs_clarification"


def test_missing_terminal() -> None:
    outcome = _map()
    assert outcome.status is RunStatus.FAILED
    assert outcome.failure_code == "missing_terminal"


def test_clean_save_completes() -> None:
    outcome = _map(saved=True, state={"plan_complete": True}, terminal_event="itinerary_done")
    assert outcome.status is RunStatus.COMPLETED
    assert outcome.failure_code is None


def test_geo_fallback_save_is_degraded() -> None:
    outcome = _map(
        saved=True,
        state={"used_geo_fallback": True},
        terminal_event="itinerary_done",
    )
    assert outcome.status is RunStatus.DEGRADED
    assert outcome.failure_code is None


def test_routing_fallback_save_is_degraded() -> None:
    outcome = _map(
        saved=True,
        state={"used_osrm_fallback": True},
        terminal_event="itinerary_done",
    )
    assert outcome.status is RunStatus.DEGRADED


def test_abort_without_trip() -> None:
    outcome = _map(terminal_event="error", terminal_data={"code": "generation_aborted"})
    assert outcome.status is RunStatus.FAILED
    assert outcome.failure_code == "generation_aborted"


def test_disconnect_cancels() -> None:
    outcome = _map(disconnected=True, terminal_event="itinerary_done", saved=True)
    assert outcome.status is RunStatus.CANCELLED
    assert outcome.failure_code == "client_disconnect"
