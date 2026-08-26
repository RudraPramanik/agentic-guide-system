"""Agent node — decides pending_tool_calls only; never invokes the tool registry (P5.9)."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from src.config import get_settings
from src.core.exceptions import WandrLLMError
from src.core.llm.client import chat_with_tools, merge_token_usage
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


def _default_tool_for_state(state: dict[str, Any]) -> str:
    """Next productive phase tool when the LLM does not pick one."""
    phase = _as_phase(state.get("agent_phase"))
    if phase == AgentPhase.DISCOVER:
        if state.get("readiness_score") is None:
            return "check_readiness"
        candidates = state.get("candidate_pois") or []
        if not isinstance(candidates, list) or not candidates:
            return "search_places"
        ranked = state.get("ranked_pois") or []
        if not isinstance(ranked, list) or not ranked:
            return "rank_places"
        return "rank_places"
    if phase == AgentPhase.PLAN:
        route = state.get("route") or []
        if isinstance(route, list) and route:
            return "build_schedule"
        return "build_route"
    return DEFAULT_TOOL_BY_PHASE.get(phase, "check_readiness")


def _synthesize_default(state: dict[str, Any]) -> list[dict[str, Any]]:
    name = _default_tool_for_state(state)
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

    token_usage = dict(state.get("token_usage") or {})
    llm_retry_count = int(state.get("llm_retry_count") or 0)

    try:
        response = await chat_with_tools(messages, tools, tool_choice="auto")
        token_usage = merge_token_usage(token_usage, response.usage)
        llm_retry_count += int(response.retry_count or 0)
        if response.tool_calls:
            return {
                "pending_tool_calls": _pending_dicts(response.tool_calls),
                "token_usage": token_usage,
                "llm_retry_count": llm_retry_count,
            }

        nudged = list(messages) + [{"role": "system", "content": _NUDGE}]
        response2 = await chat_with_tools(nudged, tools, tool_choice="required")
        token_usage = merge_token_usage(token_usage, response2.usage)
        llm_retry_count += int(response2.retry_count or 0)
        if response2.tool_calls:
            return {
                "pending_tool_calls": _pending_dicts(response2.tool_calls),
                "warnings": _append_warning(state, "agent_nudged"),
                "token_usage": token_usage,
                "llm_retry_count": llm_retry_count,
            }

        return {
            "pending_tool_calls": _synthesize_default(state),
            "warnings": _append_warning(state, "agent_no_tool_call_default_used"),
            "token_usage": token_usage,
            "llm_retry_count": llm_retry_count,
        }
    except WandrLLMError:
        return {
            "pending_tool_calls": _synthesize_default(state),
            "llm_retry_count": llm_retry_count + 1,
            "token_usage": token_usage,
            "warnings": _append_warning(state, "agent_no_tool_call_default_used"),
        }
