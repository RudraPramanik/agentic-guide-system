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
    route = state_get(state, "route") or []
    working: dict[str, Any] = dict(state) if isinstance(state, dict) else {}

    # LLM may call build_schedule before build_route (esp. after stuck phase advance).
    if not route:
        from src.planner.tools.build_route import run as build_route_run
        from src.planner.tools.schemas import BuildRouteIn

        built = await build_route_run(BuildRouteIn(), ctx, working)
        if not built.ok:
            return ToolResult(
                ok=False,
                code=built.code or "precondition_failed",
                message=built.message or "build_route required before schedule",
                data=built.data,
                fallback_used=built.fallback_used,
            )
        route = (built.data or {}).get("route") or []
        if built.data:
            working.update({k: v for k, v in built.data.items() if v is not None})
        if not route:
            return ToolResult(
                ok=False,
                code="empty_route",
                message="no route days after build_route",
                data=built.data,
            )

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

    data: dict[str, Any] = {"schedule": schedule}
    if working.get("route") is not None:
        data["route"] = working["route"]
    if working.get("ranked_pois") is not None:
        data["ranked_pois"] = working["ranked_pois"]
    if working.get("used_osrm_fallback") is not None:
        data["used_osrm_fallback"] = working["used_osrm_fallback"]

    return ToolResult(ok=True, data=data)
