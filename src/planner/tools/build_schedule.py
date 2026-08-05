"""build_schedule — PLAN; build_day_schedule per route day → day-dict schedule."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.planner.tools._helpers import dict_to_scored, state_get
from src.planner.tools.schemas import BuildScheduleIn, ToolResult
from src.travel_engine.protocols import RouteLeg, legs_to_lookup
from src.travel_engine.schedule_builder import ScheduledStop, build_day_schedule
from src.travel_engine.travel_rules import BASE_SENTINEL_ID


def _legs_from_dicts(raw: list) -> list[RouteLeg]:
    legs: list[RouteLeg] = []
    for item in raw:
        if isinstance(item, RouteLeg):
            legs.append(item)
        else:
            legs.append(RouteLeg.model_validate(item))
    return legs


def _polyline_by_place(
    ordered_raw: list,
    leg_polylines: list,
) -> dict[str, str | None]:
    """Map place_id → leg_polyline from optimize order (may diverge after morning extract)."""
    out: dict[str, str | None] = {}
    for i, item in enumerate(ordered_raw or []):
        if isinstance(item, dict):
            place = item.get("place") if isinstance(item.get("place"), dict) else item
            pid = place.get("id") if isinstance(place, dict) else None
            if pid is None and isinstance(item, dict):
                pid = item.get("place_id")
        else:
            pid = getattr(getattr(item, "place", None), "id", None)
        if pid is None:
            continue
        poly = leg_polylines[i] if i < len(leg_polylines) else None
        out[str(pid)] = poly
    return out


def _hop_travel_min(
    lookup: dict[tuple[UUID, UUID], RouteLeg],
    frm: UUID,
    to: UUID,
) -> int:
    leg = lookup.get((frm, to))
    return int(leg.duration_min) if leg is not None else 0


def _hop_distance_km(
    lookup: dict[tuple[UUID, UUID], RouteLeg],
    frm: UUID,
    to: UUID,
) -> float:
    leg = lookup.get((frm, to))
    return float(leg.distance_km) if leg is not None else 0.0


def _flat_stop(
    scheduled: ScheduledStop,
    *,
    order: int,
    travel_time_min: int,
    leg_polyline: str | None,
) -> dict[str, Any]:
    place = scheduled.place
    return {
        "place_id": str(place.id),
        "name": place.name,
        "lat": float(place.lat),
        "lng": float(place.lng),
        "category": place.category,
        "order": order,
        "travel_time_min": travel_time_min,
        "visit_duration_min": scheduled.visit_duration_min,
        "suggested_start_time": scheduled.suggested_start_time,
        "arrival_note": scheduled.arrival_note,
        "leg_polyline": leg_polyline,
        # Keep score for validate_itinerary → ScheduledStop reconstruction
        "score": scheduled.score,
    }


def _day_dict(
    day_num: int,
    day: dict,
    scheduled: list[ScheduledStop],
) -> dict[str, Any]:
    legs = _legs_from_dicts(day.get("legs") or [])
    lookup = legs_to_lookup(legs)
    poly_map = _polyline_by_place(
        day.get("ordered") or [],
        list(day.get("leg_polylines") or []),
    )

    stops_out: list[dict[str, Any]] = []
    total_distance_km = 0.0
    prev_id = BASE_SENTINEL_ID
    for i, sched in enumerate(scheduled):
        to_id = sched.place.id
        travel = _hop_travel_min(lookup, prev_id, to_id)
        total_distance_km += _hop_distance_km(lookup, prev_id, to_id)
        stops_out.append(
            _flat_stop(
                sched,
                order=i + 1,
                travel_time_min=travel,
                leg_polyline=poly_map.get(str(to_id)),
            )
        )
        prev_id = to_id

    return {
        "day": day_num,
        "stops": stops_out,
        "total_distance_km": round(total_distance_km, 3),
        "total_travel_min": int(day.get("total_travel_min") or 0),
        "day_polyline": day.get("day_polyline"),
    }


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

    schedule: list[dict[str, Any]] = []

    for day_idx, day in enumerate(route):
        if not isinstance(day, dict):
            continue
        ordered_raw = day.get("ordered") or []
        legs_raw = day.get("legs") or []
        ordered = [
            dict_to_scored(s) if isinstance(s, dict) else s for s in ordered_raw
        ]
        legs = _legs_from_dicts(legs_raw)
        timed = build_day_schedule(ordered, legs)
        schedule.append(_day_dict(day_idx + 1, day, timed))

    data: dict[str, Any] = {"schedule": schedule}
    if working.get("route") is not None:
        data["route"] = working["route"]
    if working.get("ranked_pois") is not None:
        data["ranked_pois"] = working["ranked_pois"]
    if working.get("used_osrm_fallback") is not None:
        data["used_osrm_fallback"] = working["used_osrm_fallback"]

    return ToolResult(ok=True, data=data)
