"""Flush Slice 7 role notes onto TravelState tool_trace + token_usage."""

from __future__ import annotations

from typing import Any

from src.core.llm.client import LLMUsage, merge_token_usage
from src.planner.tools.schemas import AgentPhase, ToolTraceEntry


def flush_reasoning_notes(
    state: dict[str, Any],
    notes: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Append reasoning notes to tool_trace and merge usage. No-op when empty."""
    if not notes:
        return state
    trace = list(state.get("tool_trace") or [])
    usage = dict(state.get("token_usage") or {})
    phase = state.get("agent_phase") or AgentPhase.WRAP_UP
    for note in notes:
        entry = ToolTraceEntry(
            name=str(note.get("name") or "reasoning"),
            ok=bool(note.get("ok")),
            ms=float(note.get("ms") or 0.0),
            phase=phase,
            code=str(note.get("code")) if note.get("code") is not None else None,
            diagnostics=note.get("diagnostics")
            if isinstance(note.get("diagnostics"), dict)
            else None,
        )
        trace.append(entry.model_dump(mode="json"))
        raw_usage = note.get("usage") or {}
        if isinstance(raw_usage, dict) and any(raw_usage.values()):
            usage = merge_token_usage(
                usage,
                LLMUsage(
                    prompt_tokens=int(raw_usage.get("prompt_tokens") or 0),
                    completion_tokens=int(raw_usage.get("completion_tokens") or 0),
                    total_tokens=int(raw_usage.get("total_tokens") or 0),
                ),
            )
    return {**state, "tool_trace": trace, "token_usage": usage}
