"""Planner tool I/O schemas — AgentPhase, ToolContext, ToolResult, per-tool inputs."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AgentPhase(str, Enum):
    DISCOVER = "discover"
    PLAN = "plan"
    VALIDATE = "validate"
    REPLAN = "replan"
    WRAP_UP = "wrap_up"


PHASE_TOOLS: dict[AgentPhase, list[str]] = {
    AgentPhase.DISCOVER: [
        "check_readiness",
        "search_places",
        "rank_places",
        "ask_clarification",
    ],
    AgentPhase.PLAN: ["build_route", "build_schedule"],
    AgentPhase.VALIDATE: ["validate_itinerary"],
    AgentPhase.REPLAN: [
        "reoptimize_routes",
        "drop_weakest_stop",
        "expand_poi_search",
        "accept_partial",
    ],
    AgentPhase.WRAP_UP: ["finish_plan"],
}


class ToolResult(BaseModel):
    ok: bool
    code: str | None = None
    message: str | None = None
    data: dict | None = None
    fallback_used: bool = False


class ToolTraceEntry(BaseModel):
    name: str
    ok: bool
    ms: float
    phase: AgentPhase | str
    code: str | None = None
    fallback_used: bool | None = None


class PendingToolCall(BaseModel):
    name: str
    arguments_json: str
    id: str | None = None


class ToolContext(BaseModel):
    """Non-serializable deps for tools — never put in LangGraph TravelState.

    Thread only via config["configurable"]["tool_context"]. Tools are read-only
    w.r.t. planning state; return ToolResult only.
    """

    model_config = {"arbitrary_types_allowed": True}

    destination_id: UUID
    base_lat: float
    base_lng: float
    routing: Any = None
    db: Any = None


# ── Per-tool input models (minimal; tools also read state/ctx) ──


class CheckReadinessIn(BaseModel):
    pass


class SearchPlacesIn(BaseModel):
    query: str | None = None
    top_k: int | None = None


class RankPlacesIn(BaseModel):
    pass


class BuildRouteIn(BaseModel):
    pass


class BuildScheduleIn(BaseModel):
    pass


class ValidateItineraryIn(BaseModel):
    pass


class FinishPlanIn(BaseModel):
    pass


class AskClarificationIn(BaseModel):
    question: str = ""


class ReoptimizeRoutesIn(BaseModel):
    pass


class DropWeakestStopIn(BaseModel):
    pass


class ExpandPoiSearchIn(BaseModel):
    pass


class AcceptPartialIn(BaseModel):
    pass


class ToolDefinition:
    """Registry entry — plain class so fn can be swapped after stub registration."""

    __slots__ = ("fn", "input_model", "allowed_phases", "preconditions")

    def __init__(
        self,
        fn: Any,
        input_model: type[BaseModel],
        allowed_phases: list[AgentPhase] | None = None,
        preconditions: Any = None,
    ) -> None:
        self.fn = fn
        self.input_model = input_model
        self.allowed_phases = allowed_phases or []
        self.preconditions = preconditions
