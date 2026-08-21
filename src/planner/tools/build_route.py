"""build_route — PLAN; allocate_days + optimize_route via ctx.routing."""

from __future__ import annotations

from typing import Any

from src.planner.tools._helpers import (
    dict_to_scored,
    preferences_from_state,
    scored_to_dict,
    state_get,
)
from src.planner.tools.schemas import BuildRouteIn, ToolResult
from src.travel_engine.day_allocator import allocate_days
from src.travel_engine.route_optimizer import optimize_route


def _base_coords(ctx: Any, state: Any) -> tuple[float, float] | None:
    lat = getattr(ctx, "base_lat", None) if ctx is not None else None
    lng = getattr(ctx, "base_lng", None) if ctx is not None else None
    if lat is None:
        lat = state_get(state, "base_lat")
    if lng is None:
        lng = state_get(state, "base_lng")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


async def run(
    inp: BuildRouteIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = inp
    routing = getattr(ctx, "routing", None) if ctx is not None else None
    if routing is None:
        return ToolResult(
            ok=False,
            code="precondition_failed",
            message="routing provider required",
        )
    coords = _base_coords(ctx, state)
    if coords is None:
        return ToolResult(
            ok=False,
            code="precondition_failed",
            message="base_lat/base_lng required",
        )
    base_lat, base_lng = coords

    raw_ranked = state_get(state, "ranked_pois") or []
    ranked = [dict_to_scored(r) if isinstance(r, dict) else r for r in raw_ranked]
    prefs = preferences_from_state(state)

    # LLM may skip rank_places (or stuck-advance into PLAN before ranking).
    # Auto-rank from candidates so allocate_days is never fed an empty list when
    # search already produced POIs.
    if not ranked:
        from src.planner.tools._helpers import dict_to_candidate
        from src.travel_engine.place_selector import select_places

        raw_cands = state_get(state, "candidate_pois") or []
        candidates = [
            dict_to_candidate(c) if isinstance(c, dict) else c for c in raw_cands
        ]
        if candidates:
            ranked = select_places(candidates, prefs)

    if not ranked:
        return ToolResult(
            ok=False,
            code="no_ranked_places",
            message="no ranked or candidate places to route",
        )

    days = allocate_days(ranked, prefs.days, prefs)

    route_days: list[dict] = []
    all_dropped: list[dict] = []
    used_osrm_fallback = False

    for day_places in days:
        result = await optimize_route(day_places, base_lat, base_lng, routing)
        for leg in result.legs:
            if getattr(leg, "used_fallback", False):
                used_osrm_fallback = True
        dropped = [d.model_dump(mode="json") for d in result.dropped_stops]
        all_dropped.extend(dropped)
        route_days.append(
            {
                "ordered": [scored_to_dict(s) for s in result.ordered],
                "legs": [leg.model_dump(mode="json") for leg in result.legs],
                "total_travel_min": result.total_travel_min,
                "dropped_stops": dropped,
                "still_over_budget": result.still_over_budget,
                "leg_polylines": list(result.leg_polylines),
                "day_polyline": result.day_polyline,
            }
        )

    return ToolResult(
        ok=True,
        data={
            "route": route_days,
            "ranked_pois": [scored_to_dict(s) for s in ranked],
            "dropped_stops": all_dropped,
            "used_osrm_fallback": used_osrm_fallback,
        },
        fallback_used=used_osrm_fallback,
    )
