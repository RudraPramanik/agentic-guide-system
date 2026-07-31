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
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """Sole registry runner for pending tool calls (LLM and synthesized defaults)."""
    cfg = config or {}
    configurable = cfg.get("configurable") if isinstance(cfg, dict) else None
    if not isinstance(configurable, dict):
        configurable = {}
    ctx = configurable.get("tool_context")

    working_state: dict[str, Any] = dict(state)
    pending = list(state.get("pending_tool_calls") or [])

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

    working_state["pending_tool_calls"] = []
    run_stuck_detector(working_state)
    return working_state
