"""Agent node — decides pending_tool_calls only; never invokes the tool registry (P5.9)."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.config import get_settings
from src.core.exceptions import WandrLLMError
from src.core.llm.client import chat_with_tools
from src.planner.graph.messages import build_agent_messages
from src.planner.tools.registry import get_tools_for_phase
from src.planner.tools.schemas import (
    DEFAULT_TOOL_BY_PHASE,
    AgentPhase,
    PendingToolCall,
)

_NUDGE = (
    "You must call exactly one allowed tool for the current phase. "
    "Do not reply with plain text."
)


def _as_phase(value: Any) -> AgentPhase:
    if isinstance(value, AgentPhase):
        return value
    if isinstance(value, str):
        try:
            return AgentPhase(value)
        except ValueError:
            pass
    return AgentPhase.DISCOVER


def _pending_dicts(calls: list[dict[str, Any]] | list[PendingToolCall]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for call in calls:
        if isinstance(call, PendingToolCall):
            out.append(call.model_dump())
        elif isinstance(call, dict):
            out.append(
                {
                    "name": call.get("name", ""),
                    "arguments_json": call.get("arguments_json") or "{}",
                    "id": call.get("id"),
                }
            )
    return out


def _synthesize_default(phase: AgentPhase) -> list[dict[str, Any]]:
    name = DEFAULT_TOOL_BY_PHASE.get(phase, "check_readiness")
    return [PendingToolCall(name=name, arguments_json="{}").model_dump()]


def _append_warning(state: dict[str, Any], code: str) -> list[str]:
    warnings = list(state.get("warnings") or [])
    warnings.append(code)
    return warnings


async def agent_node(
    state: dict[str, Any],
    config: RunnableConfig,
) -> dict[str, Any]:
    """ONLY decides next tools. NEVER invokes the tool registry runner itself."""
    _ = config  # ToolContext unused for decide-only path; available if needed later
    settings = get_settings()
    tool_loop_count = int(state.get("tool_loop_count") or 0)
    if tool_loop_count >= settings.PLANNER_MAX_TOOL_CALLS:
        return {
            "abort_triggered": True,
            "agent_phase": AgentPhase.WRAP_UP,
            "pending_tool_calls": [],
        }

    phase = _as_phase(state.get("agent_phase"))
    tools = get_tools_for_phase(phase)
    messages = build_agent_messages(state)

    try:
        response = await chat_with_tools(messages, tools, tool_choice="auto")
        if response.tool_calls:
            return {"pending_tool_calls": _pending_dicts(response.tool_calls)}

        nudged = list(messages) + [{"role": "system", "content": _NUDGE}]
        response2 = await chat_with_tools(nudged, tools, tool_choice="required")
        if response2.tool_calls:
            return {
                "pending_tool_calls": _pending_dicts(response2.tool_calls),
                "warnings": _append_warning(state, "agent_nudged"),
            }

        return {
            "pending_tool_calls": _synthesize_default(phase),
            "warnings": _append_warning(state, "agent_no_tool_call_default_used"),
        }
    except WandrLLMError:
        return {
            "pending_tool_calls": _synthesize_default(phase),
            "llm_retry_count": int(state.get("llm_retry_count") or 0) + 1,
            "warnings": _append_warning(state, "agent_no_tool_call_default_used"),
        }
