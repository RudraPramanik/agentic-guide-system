"""Tool executor node — sole caller of execute_tool (P5.9)."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.runnables import RunnableConfig

from src.planner.tools.registry import (
    apply_tool_result,
    execute_tool,
    maybe_transition_phase,
    parse_tool_input,
    run_stuck_detector,
)


def _call_fields(call: Any) -> tuple[str, str]:
    if isinstance(call, dict):
        return str(call.get("name") or ""), str(call.get("arguments_json") or "{}")
    name = getattr(call, "name", "") or ""
    args = getattr(call, "arguments_json", None) or "{}"
    return str(name), str(args)


async def tool_executor_node(
    state: dict[str, Any],
    config: RunnableConfig,
) -> dict[str, Any]:
    """Sole registry runner for pending tool calls (LLM and synthesized defaults)."""
    # Annotate config as RunnableConfig (not Optional) so LangGraph injects it.
    configurable = config.get("configurable") if config else None
    if not isinstance(configurable, dict):
        configurable = {}
    ctx = configurable.get("tool_context")

    emit = configurable.get("emit")
    working_state: dict[str, Any] = dict(state)
    pending = list(state.get("pending_tool_calls") or [])
    last_phase = working_state.get("agent_phase")

    for call in pending:
        name, arguments_json = _call_fields(call)
        input_model = parse_tool_input(name, arguments_json)
        started = time.perf_counter()
        result = await execute_tool(name, input_model, ctx, working_state)
        duration_ms = (time.perf_counter() - started) * 1000.0
        working_state = apply_tool_result(
            working_state, name, result, duration_ms=duration_ms
        )
        maybe_transition_phase(working_state, name, result)
        phase_now = working_state.get("agent_phase")
        if callable(emit) and phase_now != last_phase:
            emit(
                "phase_changed",
                {"phase": str(phase_now)},
                state_snapshot=dict(working_state),
            )
            last_phase = phase_now
        if callable(emit):
            emit(
                "tool_done",
                {
                    "name": name,
                    "ok": bool(result.ok),
                    "code": result.code,
                    "ms": duration_ms,
                },
                state_snapshot=dict(working_state),
            )

    working_state["pending_tool_calls"] = []
    run_stuck_detector(working_state)
    phase_after_stuck = working_state.get("agent_phase")
    if callable(emit) and phase_after_stuck != last_phase:
        emit(
            "phase_changed",
            {"phase": str(phase_after_stuck)},
            state_snapshot=dict(working_state),
        )
    if callable(emit):
        emit("tool_batch_done", {}, state_snapshot=dict(working_state))
    return working_state
