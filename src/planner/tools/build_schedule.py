"""build_schedule — PLAN; build_day_schedule per route day."""

from __future__ import annotations

from typing import Any

from src.planner.tools._helpers import dict_to_scored, state_get
from src.planner.tools.schemas import BuildScheduleIn, ToolResult
from src.travel_engine.protocols import RouteLeg
from src.travel_engine.schedule_builder import build_day_schedule


def _legs_from_dicts(raw: list) -> list[RouteLeg]:
    legs: list[RouteLeg] = []
    for item in raw:
        if isinstance(item, RouteLeg):
            legs.append(item)
        else:
            legs.append(RouteLeg.model_validate(item))
    return legs


async def run(
    inp: BuildScheduleIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = inp
    _ = ctx
    route = state_get(state, "route") or []
    schedule: list[list[dict]] = []

    for day in route:
        ordered_raw = day.get("ordered") if isinstance(day, dict) else []
        legs_raw = day.get("legs") if isinstance(day, dict) else []
        ordered = [
            dict_to_scored(s) if isinstance(s, dict) else s for s in ordered_raw
        ]
        legs = _legs_from_dicts(legs_raw or [])
        stops = build_day_schedule(ordered, legs)
        schedule.append([s.model_dump(mode="json") for s in stops])

    return ToolResult(
        ok=True,
        data={"schedule": schedule},
    )
