"""Map a finished generate onto a terminal run status. No I/O."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.exceptions import WandrLLMError
from src.planner.runs.models import RunStatus


@dataclass(frozen=True)
class RunOutcome:
    status: RunStatus
    failure_code: str | None


def _error_code(terminal_event: str | None, terminal_data: dict[str, Any] | None) -> str | None:
    if terminal_event != "error" or not terminal_data:
        return None
    code = terminal_data.get("code")
    return code if isinstance(code, str) and code else None


def _errors(state: dict[str, Any] | None) -> list[Any]:
    if not state:
        return []
    errors = state.get("errors") or []
    return errors if isinstance(errors, list) else []


def map_generate_outcome(
    *,
    disconnected: bool,
    task_error: BaseException | None,
    state: dict[str, Any] | None,
    terminal_event: str | None,
    terminal_data: dict[str, Any] | None,
    saved: bool,
) -> RunOutcome:
    """One terminal status for a generate the router can already see."""
    if disconnected:
        return RunOutcome(RunStatus.CANCELLED, "client_disconnect")

    code = _error_code(terminal_event, terminal_data)
    errors = _errors(state)
    if code == "generation_timeout" or "generation_timeout" in errors:
        return RunOutcome(RunStatus.TIMED_OUT, "generation_timeout")
    if code == "graph_recursion_limit" or "graph_recursion_limit" in errors:
        return RunOutcome(RunStatus.FAILED, "graph_recursion_limit")
    if isinstance(task_error, WandrLLMError):
        return RunOutcome(RunStatus.FAILED, "llm_unavailable")
    if state is not None and state.get("needs_clarification"):
        return RunOutcome(RunStatus.FAILED, "needs_clarification")
    if saved:
        if state is not None and (
            state.get("used_geo_fallback") or state.get("used_osrm_fallback")
        ):
            return RunOutcome(RunStatus.DEGRADED, None)
        return RunOutcome(RunStatus.COMPLETED, None)
    if terminal_event is None and task_error is None:
        return RunOutcome(RunStatus.FAILED, "missing_terminal")
    return RunOutcome(RunStatus.FAILED, "generation_aborted")
