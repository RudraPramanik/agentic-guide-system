"""Tool registry — 12 named tools, phase gating, soft-fail execute_tool.

Orchestration call order for tool_executor_node (step 5.9):
  execute_tool → apply_tool_result → maybe_transition_phase

execute_tool never merges ToolResult.data into route/schedule;
apply_tool_result is the sole TravelState writer from tool outcomes.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from pydantic import BaseModel

from src.planner.tools.orchestration import (
    _make_test_state,
    apply_tool_result,
    check_preconditions,
    maybe_transition_phase,
    run_stuck_detector,
)
from src.planner.tools.schemas import (
    AcceptPartialIn,
    AgentPhase,
    AskClarificationIn,
    BuildRouteIn,
    BuildScheduleIn,
    CheckReadinessIn,
    DropWeakestStopIn,
    ExpandPoiSearchIn,
    FinishPlanIn,
    PHASE_TOOLS,
    RankPlacesIn,
    ReoptimizeRoutesIn,
    SearchPlacesIn,
    ToolDefinition,
    ToolResult,
    ValidateItineraryIn,
)
from src.planner.tools._helpers import resolve_state, state_get

__all__ = [
    "TOOL_REGISTRY",
    "execute_tool",
    "get_tools_for_phase",
    "parse_tool_input",
    "apply_tool_result",
    "check_preconditions",
    "maybe_transition_phase",
    "run_stuck_detector",
    "_make_test_state",
]


async def _stub_fn(*_args: Any, **_kwargs: Any) -> ToolResult:
    return ToolResult(ok=False, code="not_implemented", message="stub")


def _finish_plan_ok(state: Any, _ctx: Any) -> bool:
    if state_get(state, "abort_triggered", False):
        return True
    if state_get(state, "last_validate_ok", False):
        return True
    vr = state_get(state, "validation_result")
    if vr is None:
        return False
    if isinstance(vr, dict):
        return bool(vr.get("passed") or vr.get("ok"))
    return bool(getattr(vr, "passed", False) or getattr(vr, "ok", False))


def _tool(
    fn: Callable,
    input_model: type[BaseModel],
    phases: list[AgentPhase],
    preconditions: Callable[..., bool] | None = None,
) -> ToolDefinition:
    return ToolDefinition(
        fn=fn,
        input_model=input_model,
        allowed_phases=phases,
        preconditions=preconditions,
    )


# Built below after imports of real tool modules — stubs first so import order is safe.
TOOL_REGISTRY: dict[str, ToolDefinition] = {}


def _register_stubs() -> None:
    """Register all 12 names; real fns overwrite in _wire_real_fns()."""
    mapping: list[tuple[str, type[BaseModel], list[AgentPhase], Any]] = [
        ("check_readiness", CheckReadinessIn, [AgentPhase.DISCOVER], None),
        ("search_places", SearchPlacesIn, [AgentPhase.DISCOVER], None),
        ("rank_places", RankPlacesIn, [AgentPhase.DISCOVER], None),
        ("ask_clarification", AskClarificationIn, [AgentPhase.DISCOVER], None),
        ("build_route", BuildRouteIn, [AgentPhase.PLAN], None),
        ("build_schedule", BuildScheduleIn, [AgentPhase.PLAN], None),
        ("validate_itinerary", ValidateItineraryIn, [AgentPhase.VALIDATE], None),
        (
            "reoptimize_routes",
            ReoptimizeRoutesIn,
            [AgentPhase.REPLAN],
            None,
        ),
        (
            "drop_weakest_stop",
            DropWeakestStopIn,
            [AgentPhase.REPLAN],
            None,
        ),
        (
            "expand_poi_search",
            ExpandPoiSearchIn,
            [AgentPhase.REPLAN],
            None,
        ),
        ("accept_partial", AcceptPartialIn, [AgentPhase.REPLAN], None),
        (
            "finish_plan",
            FinishPlanIn,
            [AgentPhase.WRAP_UP],
            _finish_plan_ok,
        ),
    ]
    for name, model, phases, pre in mapping:
        TOOL_REGISTRY[name] = _tool(_stub_fn, model, phases, pre)


_register_stubs()


def _wire_real_fns() -> None:
    """Import tool modules and replace stub fns."""
    from src.planner.tools.accept_partial import run as accept_partial_run
    from src.planner.tools.ask_clarification import run as ask_clarification_run
    from src.planner.tools.build_route import run as build_route_run
    from src.planner.tools.build_schedule import run as build_schedule_run
    from src.planner.tools.check_readiness import run as check_readiness_run
    from src.planner.tools.drop_weakest_stop import run as drop_weakest_stop_run
    from src.planner.tools.expand_poi_search import run as expand_poi_search_run
    from src.planner.tools.finish_plan import run as finish_plan_run
    from src.planner.tools.rank_places import run as rank_places_run
    from src.planner.tools.reoptimize_routes import run as reoptimize_routes_run
    from src.planner.tools.search_places import run as search_places_run
    from src.planner.tools.validate_itinerary import run as validate_itinerary_run

    TOOL_REGISTRY["check_readiness"].fn = check_readiness_run
    TOOL_REGISTRY["search_places"].fn = search_places_run
    TOOL_REGISTRY["rank_places"].fn = rank_places_run
    TOOL_REGISTRY["ask_clarification"].fn = ask_clarification_run
    TOOL_REGISTRY["build_route"].fn = build_route_run
    TOOL_REGISTRY["build_schedule"].fn = build_schedule_run
    TOOL_REGISTRY["validate_itinerary"].fn = validate_itinerary_run
    TOOL_REGISTRY["reoptimize_routes"].fn = reoptimize_routes_run
    TOOL_REGISTRY["drop_weakest_stop"].fn = drop_weakest_stop_run
    TOOL_REGISTRY["expand_poi_search"].fn = expand_poi_search_run
    TOOL_REGISTRY["accept_partial"].fn = accept_partial_run
    TOOL_REGISTRY["finish_plan"].fn = finish_plan_run


def get_tools_for_phase(phase: AgentPhase) -> list[dict]:
    """OpenAI function schemas filtered by PHASE_TOOLS[phase]."""
    names = PHASE_TOOLS.get(phase, [])
    out: list[dict] = []
    for name in names:
        defn = TOOL_REGISTRY.get(name)
        if defn is None:
            continue
        schema = defn.input_model.model_json_schema()
        out.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": name.replace("_", " "),
                    "parameters": schema,
                },
            }
        )
    return out


def parse_tool_input(name: str, arguments_json: str | None) -> BaseModel:
    """Parse LLM tool args into the tool's Pydantic model. Soft-fail — never raises."""
    defn = TOOL_REGISTRY.get(name)
    model_cls = defn.input_model if defn is not None else CheckReadinessIn
    raw = arguments_json if arguments_json is not None else "{}"
    try:
        data = json.loads(raw) if str(raw).strip() else {}
        if not isinstance(data, dict):
            data = {}
        return model_cls.model_validate(data)
    except Exception:  # noqa: BLE001 — soft-fail for executor
        try:
            return model_cls()
        except Exception:  # noqa: BLE001
            return CheckReadinessIn()


async def execute_tool(
    name: str,
    input: BaseModel | dict,  # noqa: A002 — locked signature
    ctx: object | None = None,
    state: Any = None,
) -> ToolResult:
    """Dispatch by name. Soft-fail unknown / wrong-phase / precondition / errors.

    Does not mutate planning state. Callers must run:
    apply_tool_result(state, name, result) then maybe_transition_phase(...).
    """
    if name not in TOOL_REGISTRY:
        return ToolResult(
            ok=False,
            code="unknown_tool",
            message=f"unknown tool: {name}",
            data=None,
        )

    defn = TOOL_REGISTRY[name]
    view = resolve_state(ctx, state)
    ok_pre, pre_msg = check_preconditions(name, view, ctx)
    if not ok_pre:
        return ToolResult(
            ok=False,
            code="precondition_failed",
            message=pre_msg,
            data=None,
        )

    try:
        if isinstance(input, dict):
            parsed = defn.input_model.model_validate(input)
        elif isinstance(input, defn.input_model):
            parsed = input
        elif isinstance(input, BaseModel):
            # Allow Empty() from step validations — coerce empty models
            parsed = defn.input_model.model_validate(input.model_dump())
        else:
            parsed = defn.input_model()
        return await defn.fn(parsed, ctx, view)
    except Exception as exc:  # noqa: BLE001 — never raise to graph
        return ToolResult(
            ok=False,
            code="tool_error",
            message=str(exc),
            data=None,
        )


_wire_real_fns()
