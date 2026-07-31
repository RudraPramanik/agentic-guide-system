"""Phase orchestration — apply_tool_result, transitions, preconditions.

Call order for tool_executor_node (step 5.9):
  execute_tool → apply_tool_result → maybe_transition_phase

apply_tool_result is the sole TravelState writer from tool outcomes.
Stuck-detector (step 5.9) must run every cycle; unknown_tool does not
increment tool_loop_count (safe only because of that detector).
"""

from __future__ import annotations

from typing import Any

from src.config import get_settings
from src.planner.tools._helpers import state_get
from src.planner.tools.schemas import AgentPhase, ToolResult, ToolTraceEntry

# Keys tools may write via ToolResult.data (never invent place IDs here).
_MERGE_KEYS = frozenset(
    {
        "candidate_pois",
        "ranked_pois",
        "explanations",
        "route",
        "schedule",
        "validation_result",
        "last_validate_ok",
        "readiness_score",
        "tier",
        "place_count",
        "enriched_pct",
        "used_geo_fallback",
        "used_osrm_fallback",
        "abort_triggered",
        "plan_complete",
        "needs_clarification",
        "clarification_question",
        "itinerary",
        "dropped_stops",
        "search_top_k",
    }
)

_LIST_APPEND_KEYS = frozenset({"warnings", "errors"})

_REPLAN_TOOLS = frozenset(
    {
        "reoptimize_routes",
        "drop_weakest_stop",
        "expand_poi_search",
        "accept_partial",
    }
)


def _state_set(state: Any, key: str, value: Any) -> None:
    if isinstance(state, dict):
        state[key] = value
    else:
        setattr(state, key, value)


def _phase_from_state(state: Any) -> AgentPhase | None:
    raw = state_get(state, "agent_phase")
    if raw is None:
        return None
    if isinstance(raw, AgentPhase):
        return raw
    try:
        return AgentPhase(str(raw))
    except ValueError:
        return None


def _make_test_state(
    *,
    agent_phase: AgentPhase = AgentPhase.DISCOVER,
    tool_loop_count: int = 0,
    replan_loop_count: int = 0,
    max_replan_attempts: int | None = None,
    abort_triggered: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    """Minimal mutable planning snapshot for unit / step validations."""
    settings = get_settings()
    state: dict[str, Any] = {
        "agent_phase": agent_phase,
        "tool_loop_count": int(tool_loop_count),
        "tool_trace": [],
        "replan_loop_count": int(replan_loop_count),
        "max_replan_attempts": (
            settings.PLANNER_MAX_REPLAN_ATTEMPTS
            if max_replan_attempts is None
            else int(max_replan_attempts)
        ),
        "abort_triggered": abort_triggered,
        "needs_clarification": False,
        "route": None,
        "schedule": None,
        "warnings": [],
        "errors": [],
    }
    state.update(extra)
    return state


def check_preconditions(
    name: str,
    state: Any,
    ctx: Any = None,
) -> tuple[bool, str | None]:
    """Phase membership + registered tool preconditions (e.g. finish_plan)."""
    from src.planner.tools.registry import TOOL_REGISTRY

    if name not in TOOL_REGISTRY:
        return False, "unknown_tool"

    defn = TOOL_REGISTRY[name]
    phase = _phase_from_state(state)
    if defn.allowed_phases:
        if phase is None or phase not in defn.allowed_phases:
            return False, f"tool {name} not allowed in phase {phase}"

    if defn.preconditions is not None:
        try:
            if not defn.preconditions(state, ctx):
                return False, f"precondition failed for {name}"
        except Exception as exc:  # noqa: BLE001 — soft-fail
            return False, str(exc)

    return True, None


def apply_tool_result(
    state: Any,
    name: str,
    result: ToolResult,
    *,
    duration_ms: float = 0.0,
) -> Any:
    """SOLE writer of planning state from tool outcomes. Never raises."""
    try:
        from src.planner.tools.registry import TOOL_REGISTRY

        # Bookkeeping: resolved registry names increment; unknown_tool does not.
        # Safe only because step 5.9 stuck-detector runs every cycle.
        if name in TOOL_REGISTRY and result.code != "unknown_tool":
            count = int(state_get(state, "tool_loop_count", 0) or 0)
            _state_set(state, "tool_loop_count", count + 1)

        data = result.data if isinstance(result.data, dict) else None
        if data:
            for key, value in data.items():
                if key in _LIST_APPEND_KEYS:
                    existing = list(state_get(state, key) or [])
                    if isinstance(value, list):
                        existing.extend(value)
                    elif value is not None:
                        existing.append(value)
                    _state_set(state, key, existing)
                elif key in _MERGE_KEYS:
                    _state_set(state, key, value)

        phase = _phase_from_state(state) or AgentPhase.DISCOVER
        entry = ToolTraceEntry(
            name=name,
            ok=bool(result.ok),
            ms=float(duration_ms),
            phase=phase,
            code=result.code,
            fallback_used=result.fallback_used,
        )
        trace = list(state_get(state, "tool_trace") or [])
        trace.append(entry.model_dump(mode="json"))
        _state_set(state, "tool_trace", trace)
    except Exception:  # noqa: BLE001 — never raise to graph
        pass
    return state


def maybe_transition_phase(
    state: Any,
    tool_name: str,
    result: ToolResult,
) -> None:
    """Apply locked transition table. LLM never sets agent_phase."""
    settings = get_settings()
    max_tools = settings.PLANNER_MAX_TOOL_CALLS
    loop_count = int(state_get(state, "tool_loop_count", 0) or 0)
    if loop_count >= max_tools:
        _state_set(state, "agent_phase", AgentPhase.WRAP_UP)
        _state_set(state, "abort_triggered", True)
        return

    phase = _phase_from_state(state)
    if phase is None:
        return

    max_replan = state_get(state, "max_replan_attempts")
    if max_replan is None:
        max_replan = settings.PLANNER_MAX_REPLAN_ATTEMPTS
    max_replan = int(max_replan)
    replan_count = int(state_get(state, "replan_loop_count", 0) or 0)
    ok = bool(result.ok)

    if phase == AgentPhase.DISCOVER:
        if tool_name == "rank_places" and ok:
            _state_set(state, "agent_phase", AgentPhase.PLAN)
            return
        if tool_name == "ask_clarification" and ok:
            _state_set(state, "needs_clarification", True)
            return

    if phase == AgentPhase.PLAN:
        if tool_name == "build_schedule" and ok:
            _state_set(state, "agent_phase", AgentPhase.VALIDATE)
            return

    if phase == AgentPhase.VALIDATE:
        if tool_name == "validate_itinerary":
            if ok:
                _state_set(state, "agent_phase", AgentPhase.WRAP_UP)
                return
            # errors / not-ok
            if replan_count < max_replan:
                _state_set(state, "agent_phase", AgentPhase.REPLAN)
                _state_set(state, "replan_loop_count", replan_count + 1)
                return
            _state_set(state, "agent_phase", AgentPhase.WRAP_UP)
            _state_set(state, "abort_triggered", True)
            return

    if phase == AgentPhase.REPLAN:
        if tool_name == "accept_partial" and ok:
            _state_set(state, "agent_phase", AgentPhase.WRAP_UP)
            return
        if replan_count >= max_replan:
            _state_set(state, "agent_phase", AgentPhase.WRAP_UP)
            _state_set(state, "abort_triggered", True)
            return
        if tool_name in _REPLAN_TOOLS and tool_name != "accept_partial" and ok:
            _state_set(state, "agent_phase", AgentPhase.PLAN)
            return


_HAPPY_PATH_NEXT: dict[AgentPhase, AgentPhase] = {
    AgentPhase.DISCOVER: AgentPhase.PLAN,
    AgentPhase.PLAN: AgentPhase.VALIDATE,
    AgentPhase.VALIDATE: AgentPhase.WRAP_UP,
}


def _progress_fingerprint(state: Any) -> str:
    """Compact progress signature for stuck detection."""
    phase = _phase_from_state(state) or AgentPhase.DISCOVER
    candidates = state_get(state, "candidate_pois") or []
    ranked = state_get(state, "ranked_pois") or []
    route = state_get(state, "route") or []
    schedule = state_get(state, "schedule") or []
    codes: list[str] = []
    vr = state_get(state, "validation_result")
    if isinstance(vr, dict):
        errs = vr.get("errors") or []
        if isinstance(errs, list):
            codes = [str(e)[:80] for e in errs[:5]]
        elif errs:
            codes = [str(errs)[:80]]
    return (
        f"{phase.value}|c={len(candidates)}|r={len(ranked)}|"
        f"rt={len(route)}|s={len(schedule)}|v={','.join(codes)}"
    )


def run_stuck_detector(state: Any) -> None:
    """Unconditional end-of-cycle stuck check. Mutates state in place; never raises."""
    try:
        settings = get_settings()
        limit = int(settings.PLANNER_AGENT_PHASE_STUCK_LIMIT)
        fp = _progress_fingerprint(state)
        prev = state_get(state, "stuck_fingerprint")
        cycles = int(state_get(state, "stuck_cycles", 0) or 0)
        if prev == fp:
            cycles += 1
        else:
            cycles = 1
        _state_set(state, "stuck_fingerprint", fp)
        _state_set(state, "stuck_cycles", cycles)
        if cycles < limit:
            return

        phase = _phase_from_state(state) or AgentPhase.DISCOVER
        warnings = list(state_get(state, "warnings") or [])

        if phase in (AgentPhase.DISCOVER, AgentPhase.PLAN, AgentPhase.VALIDATE):
            nxt = _HAPPY_PATH_NEXT[phase]
            _state_set(state, "agent_phase", nxt)
            warnings.append("phase_stuck_auto_advance")
            _state_set(state, "warnings", warnings)
            _state_set(state, "stuck_cycles", 0)
            return

        if phase == AgentPhase.REPLAN:
            _state_set(state, "abort_triggered", True)
            _state_set(state, "agent_phase", AgentPhase.WRAP_UP)
            warnings.append("phase_stuck_replan_abort")
            _state_set(state, "warnings", warnings)
            _state_set(state, "stuck_cycles", 0)
            return

        # WRAP_UP: force bookend exit path
        _state_set(state, "plan_complete", True)
        warnings.append("phase_stuck_wrap_up_force_complete")
        _state_set(state, "warnings", warnings)
        _state_set(state, "stuck_cycles", 0)
    except Exception:  # noqa: BLE001 — never raise to graph
        pass
