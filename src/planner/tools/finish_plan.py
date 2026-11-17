"""finish_plan — WRAP_UP; assemble final itinerary signal (precondition in registry)."""

from __future__ import annotations

from typing import Any

from src.planner.tools._helpers import state_get
from src.planner.tools.schemas import (
    BuildScheduleIn,
    FinishPlanIn,
    ToolResult,
    ValidateItineraryIn,
)


def _has_stops(schedule: Any) -> bool:
    if not isinstance(schedule, list):
        return False
    for day in schedule:
        if isinstance(day, dict) and day.get("stops"):
            return True
    return False


async def run(
    inp: FinishPlanIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    """Publish the itinerary and the engine verdict for that itinerary.

    A model may finish from a route before it calls build_schedule or
    validate_itinerary. The published plan still carries both, so the golden
    gate reads the engine result instead of an unanswered check.
    """
    _ = inp
    working = dict(state) if isinstance(state, dict) else {}
    schedule = state_get(state, "schedule") or []
    route = state_get(state, "route") or []
    data: dict[str, Any] = {}

    if not _has_stops(schedule) and route:
        from src.planner.tools.build_schedule import run as build_schedule_run

        built = await build_schedule_run(BuildScheduleIn(), ctx, working)
        if built.ok and isinstance(built.data, dict):
            schedule = built.data.get("schedule") or schedule
            route = built.data.get("route") or route
            data["schedule"] = schedule
            if built.data.get("route") is not None:
                data["route"] = route
            working = {**working, "schedule": schedule, "route": route}

    from src.planner.tools.validate_itinerary import run as validate_run

    validated = await validate_run(
        ValidateItineraryIn(),
        ctx,
        {**working, "schedule": schedule, "route": route},
    )
    if isinstance(validated.data, dict):
        data["validation_result"] = validated.data.get("validation_result")
        data["last_validate_ok"] = validated.data.get("last_validate_ok")

    data["plan_complete"] = True
    data["itinerary"] = {
        "schedule": schedule,
        "route": route,
        "days": len(schedule) or len(route),
    }
    return ToolResult(ok=True, data=data)
