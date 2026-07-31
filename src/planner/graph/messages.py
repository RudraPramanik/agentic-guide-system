"""Compact agent messages for chat_with_tools (P5.7)."""

from __future__ import annotations

from typing import Any

from src.planner.graph.state import TravelState
from src.planner.tools.schemas import PHASE_TOOLS, AgentPhase

_TOOL_TRACE_LIMIT = 5


def _as_phase(value: Any) -> AgentPhase:
    if isinstance(value, AgentPhase):
        return value
    if isinstance(value, str):
        try:
            return AgentPhase(value)
        except ValueError:
            pass
    return AgentPhase.DISCOVER


def _has_dropped_stops(route: Any) -> bool:
    if not isinstance(route, list):
        return False
    for day in route:
        if not isinstance(day, dict):
            continue
        dropped = day.get("dropped_stops") or []
        if dropped:
            return True
    return False


def _validation_errors(state: dict[str, Any]) -> list[str]:
    errors = state.get("errors") or []
    if isinstance(errors, list) and errors:
        return [str(e) for e in errors[-5:]]
    result = state.get("validation_result")
    if isinstance(result, dict):
        vr_errors = result.get("errors") or []
        if isinstance(vr_errors, list):
            return [str(e) for e in vr_errors[-5:]]
    return []


def _format_tool_trace(entries: list[Any]) -> str:
    if not entries:
        return "(none)"
    lines: list[str] = []
    for entry in entries[-_TOOL_TRACE_LIMIT:]:
        if isinstance(entry, dict):
            name = entry.get("name", "?")
            ok = entry.get("ok")
            code = entry.get("code")
            ms = entry.get("ms")
            lines.append(f"- {name} ok={ok} code={code} ms={ms}")
        else:
            lines.append(f"- {entry}")
    return "\n".join(lines)


def build_agent_messages(state: TravelState | dict[str, Any]) -> list[dict]:
    """Build system (+ optional user) messages for the tool-loop agent."""
    data: dict[str, Any] = dict(state) if state is not None else {}
    phase = _as_phase(data.get("agent_phase"))
    allowed = PHASE_TOOLS.get(phase, [])
    days = data.get("days")
    interests = data.get("interests") or []
    candidates = data.get("candidate_pois") or []
    ranked = data.get("ranked_pois") or []
    route = data.get("route") or []
    dropped = _has_dropped_stops(route)
    tool_trace = data.get("tool_trace") or []

    lines = [
        "You are a trip planner tool-using agent.",
        f"Current phase: {phase.value}.",
        f"Allowed tools for this phase only: {', '.join(allowed)}.",
        "Hard rules: never invent places, place IDs, coordinates, times, or stop order.",
        "Call tools to act; do not invent tool names outside the allowed list.",
        (
            "State summary: "
            f"days={days if days is not None else 'unknown'}, "
            f"interests={list(interests)}, "
            f"candidate_pois={len(candidates) if isinstance(candidates, list) else 0}, "
            f"ranked_pois={len(ranked) if isinstance(ranked, list) else 0}, "
            f"validation_errors={_validation_errors(data)}, "
            f"any_day_has_dropped_stops={dropped}."
        ),
        f"Recent tool_trace (last {_TOOL_TRACE_LIMIT}):\n{_format_tool_trace(list(tool_trace) if isinstance(tool_trace, list) else [])}",
    ]
    if phase == AgentPhase.REPLAN and dropped:
        lines.append(
            "REPLAN guidance: dropped_stops are present — prefer expand_poi_search "
            "over drop_weakest_stop."
        )

    messages: list[dict] = [{"role": "system", "content": "\n".join(lines)}]
    raw_input = data.get("raw_input")
    if raw_input:
        messages.append({"role": "user", "content": str(raw_input)})
    return messages
