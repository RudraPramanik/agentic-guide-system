"""drop_weakest_stop — REPLAN; drop lowest-scored stop on worst day; re-route."""

from __future__ import annotations

from typing import Any

from src.planner.tools._helpers import dict_to_scored, scored_to_dict, state_get
from src.planner.tools.build_route import run as build_route_run
from src.planner.tools.build_schedule import run as build_schedule_run
from src.planner.tools.schemas import (
    BuildRouteIn,
    BuildScheduleIn,
    DropWeakestStopIn,
    ToolResult,
)
from src.planner.tools.reoptimize_routes import _StateView


async def run(
    inp: DropWeakestStopIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = inp
    route = list(state_get(state, "route") or [])
    if not route:
        # Fall back to ranked set via full rebuild
        return await _rebuild(ctx, state, note="no_route_rebuild")

    # Worst day = highest total_travel_min (ties → first)
    worst_i = max(
        range(len(route)),
        key=lambda i: (
            int((route[i] or {}).get("total_travel_min") or 0),
            -i,
        ),
    )
    day = dict(route[worst_i] or {})
    ordered = [
        dict_to_scored(s) if isinstance(s, dict) else s
        for s in (day.get("ordered") or [])
    ]
    if len(ordered) <= 1:
        return ToolResult(
            ok=True,
            code="nothing_to_drop",
            message="day has ≤1 stop; prefer expand_poi_search",
            data={"route": route, "schedule": state_get(state, "schedule")},
        )

    victim = min(ordered, key=lambda s: (s.score, s.place.name, str(s.place.id)))
    remaining = [s for s in ordered if s.place.id != victim.place.id]

    # Rebuild ranked list without victim, then reoptimize all days
    ranked_raw = state_get(state, "ranked_pois") or []
    ranked = [dict_to_scored(r) if isinstance(r, dict) else r for r in ranked_raw]
    if ranked:
        new_ranked = [s for s in ranked if s.place.id != victim.place.id]
    else:
        new_ranked = remaining

    view = _StateView(
        state,
        {"ranked_pois": [scored_to_dict(s) for s in new_ranked]},
    )
    result = await _rebuild(
        ctx,
        view,
        note=f"dropped {victim.place.name}",
        dropped_id=str(victim.place.id),
    )
    return result


async def _rebuild(
    ctx: Any,
    state: Any,
    *,
    note: str,
    dropped_id: str | None = None,
) -> ToolResult:
    route_result = await build_route_run(BuildRouteIn(), ctx, state)
    if not route_result.ok:
        return route_result
    merged = dict(route_result.data or {})
    if dropped_id:
        merged["last_dropped_place_id"] = dropped_id
    merged["drop_note"] = note
    view = _StateView(state, merged)
    sched = await build_schedule_run(BuildScheduleIn(), ctx, view)
    data = {**merged, **(sched.data or {})}
    return ToolResult(
        ok=sched.ok,
        code=sched.code,
        message=sched.message or note,
        data=data,
        fallback_used=route_result.fallback_used or sched.fallback_used,
    )
