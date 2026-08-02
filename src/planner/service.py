"""PlannerService — generation runner with emit bridge + wait_for ceiling (P5.12).

HTTP StreamingResponse / SSE queue is P6. Happy-path may double-write TripEvaluation
(graph node + service); accepted for P5 append-only analytics.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any
from uuid import UUID

from langgraph.errors import GraphRecursionError

from src.config import get_settings
from src.planner.graph.builder import get_compiled_graph
from src.planner.graph.nodes.record_evaluation import record_evaluation
from src.planner.routing_provider import OsrmRoutingProvider
from src.planner.tools.schemas import AgentPhase, ToolContext

# Bookend nodes outside the agent↔executor cycle (parse + narrative + eval).
_GRAPH_BOOKEND_STEPS = 4
# Worst-case stuck auto-advance: DISCOVER→PLAN→VALIDATE→WRAP_UP (4 phases).
_STUCK_PHASE_HOPS = 4


def _as_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _recursion_limit(settings: Any) -> int:
    """LangGraph steps needed for max tool cycles + stuck auto-advances + bookends.

    Each tool cycle is agent + tool_executor (2 steps). Default LangGraph limit (25)
    is too low when stuck auto-advances through happy-path phases.
    """
    max_tools = int(settings.PLANNER_MAX_TOOL_CALLS)
    stuck = int(settings.PLANNER_AGENT_PHASE_STUCK_LIMIT)
    return max_tools * 2 + stuck * _STUCK_PHASE_HOPS * 2 + _GRAPH_BOOKEND_STEPS


def _initial_state(
    *,
    destination_id: UUID | str,
    raw_input: str,
    base_lat: float,
    base_lng: float,
    session_id: str,
) -> dict[str, Any]:
    settings = get_settings()
    dest = str(destination_id)
    return {
        "destination_id": dest,
        "raw_input": raw_input,
        "base_lat": float(base_lat),
        "base_lng": float(base_lng),
        "session_id": session_id,
        "agent_phase": AgentPhase.DISCOVER,
        "tool_loop_count": 0,
        "pending_tool_calls": [],
        "tool_trace": [],
        "plan_complete": False,
        "needs_clarification": False,
        "clarification_question": None,
        "replan_loop_count": 0,
        "max_replan_attempts": settings.PLANNER_MAX_REPLAN_ATTEMPTS,
        "abort_triggered": False,
        "llm_retry_count": 0,
        "used_geo_fallback": False,
        "used_osrm_fallback": False,
        "candidate_pois": [],
        "ranked_pois": [],
        "route": [],
        "schedule": [],
        "itinerary": {},
        "errors": [],
        "warnings": [],
    }


class PlannerService:
    """Service-level generation runner — not an HTTP router."""

    async def generate(
        self,
        *,
        destination_id: UUID | str,
        raw_input: str,
        base_lat: float,
        base_lng: float,
        session_id: str,
        on_event: Callable[[str, dict], None] | None = None,
        routing: Any | None = None,
    ) -> dict[str, Any]:
        """Run compiled planner graph with timeout + emit checkpoints.

        ``routing`` is optional (tests inject FakeRoutingProvider); production
        uses OsrmRoutingProvider. Always persists evaluation after return/timeout.
        """
        settings = get_settings()
        dest_uuid = _as_uuid(destination_id)
        last_known_state: dict[str, Any] = {}

        def _capture_and_emit(
            event: str,
            data: dict,
            state_snapshot: dict[str, Any] | None = None,
        ) -> None:
            if state_snapshot is not None:
                last_known_state.clear()
                last_known_state.update(state_snapshot)
            if on_event:
                on_event(event, data)

        ctx = ToolContext(
            destination_id=dest_uuid,
            base_lat=float(base_lat),
            base_lng=float(base_lng),
            routing=routing if routing is not None else OsrmRoutingProvider(),
            db=None,
        )
        initial = _initial_state(
            destination_id=dest_uuid,
            raw_input=raw_input,
            base_lat=base_lat,
            base_lng=base_lng,
            session_id=session_id,
        )
        # Seed last_known so a pre-emit timeout still has destination_id for eval.
        last_known_state.update(initial)

        graph = get_compiled_graph()
        config = {
            "configurable": {
                "tool_context": ctx,
                "emit": _capture_and_emit,
            },
            "recursion_limit": _recursion_limit(settings),
        }

        try:
            final = await asyncio.wait_for(
                graph.ainvoke(initial, config=config),
                timeout=settings.PLANNER_GENERATION_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            errors = list(last_known_state.get("errors") or [])
            errors.append("generation_timeout")
            final = {
                **last_known_state,
                "errors": errors,
                "abort_triggered": True,
            }
            _capture_and_emit("error", {"code": "generation_timeout"})
        except GraphRecursionError:
            # Bound exceeded despite settings-derived limit — controlled abort.
            errors = list(last_known_state.get("errors") or [])
            errors.append("graph_recursion_limit")
            final = {
                **last_known_state,
                "errors": errors,
                "abort_triggered": True,
            }
            _capture_and_emit("error", {"code": "graph_recursion_limit"})

        eval_update = await record_evaluation(final)
        if eval_update.get("warnings"):
            warnings = list(final.get("warnings") or [])
            warnings.extend(eval_update["warnings"])
            final = {**final, "warnings": warnings}
        return final
