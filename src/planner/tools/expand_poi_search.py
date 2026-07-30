"""expand_poi_search — REPLAN; widen top_k then search→rank→route→schedule."""

from __future__ import annotations

import math
from typing import Any

from src.planner.tools._helpers import state_get
from src.planner.tools.constants import SEARCH_DEFAULT_TOP_K, SEARCH_EXPAND_FACTOR
from src.planner.tools.rank_places import run as rank_places_run
from src.planner.tools.reoptimize_routes import _StateView
from src.planner.tools.build_route import run as build_route_run
from src.planner.tools.build_schedule import run as build_schedule_run
from src.planner.tools.schemas import (
    BuildRouteIn,
    BuildScheduleIn,
    ExpandPoiSearchIn,
    RankPlacesIn,
    SearchPlacesIn,
    ToolResult,
)
from src.planner.tools.search_places import run as search_places_run


async def run(
    inp: ExpandPoiSearchIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = inp
    current = state_get(state, "search_top_k") or SEARCH_DEFAULT_TOP_K
    new_top_k = max(1, int(math.ceil(float(current) * SEARCH_EXPAND_FACTOR)))

    search = await search_places_run(
        SearchPlacesIn(top_k=new_top_k),
        ctx,
        state,
    )
    if not search.ok:
        return search

    view1 = _StateView(
        state,
        {
            **(search.data or {}),
            "search_top_k": new_top_k,
        },
    )
    rank = await rank_places_run(RankPlacesIn(), ctx, view1)
    if not rank.ok:
        return ToolResult(
            ok=False,
            code=rank.code or "tool_error",
            message=rank.message,
            data={**(search.data or {}), **(rank.data or {})},
            fallback_used=search.fallback_used,
        )

    view2 = _StateView(
        state,
        {
            **(search.data or {}),
            **(rank.data or {}),
            "search_top_k": new_top_k,
        },
    )
    route = await build_route_run(BuildRouteIn(), ctx, view2)
    if not route.ok:
        return route

    view3 = _StateView(state, {**(view2._overrides), **(route.data or {})})
    sched = await build_schedule_run(BuildScheduleIn(), ctx, view3)
    data = {
        **(search.data or {}),
        **(rank.data or {}),
        **(route.data or {}),
        **(sched.data or {}),
        "search_top_k": new_top_k,
        "expanded_from_top_k": int(current),
    }
    return ToolResult(
        ok=sched.ok,
        code=sched.code,
        message=sched.message,
        data=data,
        fallback_used=any(
            [
                search.fallback_used,
                rank.fallback_used,
                route.fallback_used,
                sched.fallback_used,
            ]
        ),
    )
