"""LangGraph TravelState — serializable planner graph state (P5.6).

List fields (`tool_trace`, `warnings`, `errors`) are last-write-wins: nodes MUST
read-append-return the full extended list. Do NOT use Annotated reducers in P5.

FORBIDDEN on TravelState: db, routing, ToolContext, AsyncSession, httpx clients.
Thread those via config[\"configurable\"][\"tool_context\"] only.
`max_replan_attempts` default comes from get_settings().PLANNER_MAX_REPLAN_ATTEMPTS
at graph invoke time.
"""

from __future__ import annotations

from typing import Any, TypedDict


class TravelState(TypedDict, total=False):
    # Input
    destination_id: str
    destination_name: str
    destination_lat: float
    destination_lng: float
    raw_input: str
    session_id: str
    base_lat: float
    base_lng: float

    # Parsed prefs (from parse_preferences)
    days: int
    budget: str
    interests: list[str]
    include_offbeat: bool
    include_trekking: bool

    # Agent loop — agent_phase is AgentPhase value (str enum); avoid importing tools here
    agent_phase: str
    tool_loop_count: int
    pending_tool_calls: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]
    plan_complete: bool
    needs_clarification: bool
    clarification_question: str | None

    # Resilience
    replan_loop_count: int
    max_replan_attempts: int
    abort_triggered: bool
    llm_retry_count: int
    used_geo_fallback: bool
    used_osrm_fallback: bool
    readiness_score: float | None

    # Working data
    candidate_pois: list[Any]
    ranked_pois: list[Any]
    route: list[Any]
    schedule: list[Any]
    itinerary: dict[str, Any]
    validation_result: Any

    # Output
    errors: list[str]
    warnings: list[str]
    trace_id: str

    # Loop-internal stuck detector (not checkpointed across requests by design intent)
    stuck_fingerprint: str
    stuck_cycles: int
