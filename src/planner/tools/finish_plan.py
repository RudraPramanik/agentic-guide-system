"""finish_plan — WRAP_UP; assemble final itinerary signal (precondition in registry)."""

from __future__ import annotations

from typing import Any

from src.planner.tools._helpers import state_get
from src.planner.tools.schemas import FinishPlanIn, ToolResult


async def run(
    inp: FinishPlanIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = inp
    _ = ctx
    schedule = state_get(state, "schedule") or []
    route = state_get(state, "route") or []
    return ToolResult(
        ok=True,
        data={
            "plan_complete": True,
            "itinerary": {
                "schedule": schedule,
                "route": route,
                "days": len(schedule) or len(route),
            },
        },
    )
