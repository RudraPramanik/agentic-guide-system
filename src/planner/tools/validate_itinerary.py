"""validate_itinerary — VALIDATE; map state → TripItinerary → validate_trip."""

from __future__ import annotations

from typing import Any, Literal, cast
from uuid import UUID

import structlog

from src.config import get_settings
from src.planner.tools._helpers import state_get
from src.planner.tools.schemas import ToolResult, ValidateItineraryIn
from src.travel_engine.findings import collect_findings
from src.travel_engine.place_selector import PlaceCandidate
from src.travel_engine.protocols import RouteLeg, legs_to_lookup
from src.travel_engine.route_optimizer import DroppedStop
from src.travel_engine.schedule_builder import ScheduledStop
from src.travel_engine.trip_validator import DayPlan, TripItinerary, validate_trip

log = structlog.get_logger()

_HOURS_STATUS = frozenset({"verified", "unknown", "malformed"})


def _as_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _scheduled_from_flat(stop: dict) -> ScheduledStop:
    """Rebuild ScheduledStop from P6.0 flat stop dict (or nested legacy dump)."""
    if "place" in stop and isinstance(stop["place"], dict):
        return ScheduledStop.model_validate(stop)
    status = str(stop.get("opening_hours_status") or "unknown")
    if status not in _HOURS_STATUS:
        status = "unknown"
    place = PlaceCandidate(
        id=_as_uuid(stop["place_id"]),
        name=str(stop.get("name") or ""),
        category=str(stop.get("category") or "attraction"),
        enriched_tags=list(stop.get("enriched_tags") or []),
        lat=float(stop.get("lat") or 0.0),
        lng=float(stop.get("lng") or 0.0),
        evidence_count=int(stop.get("evidence_count") or 0),
        opening_hours_status=cast(
            Literal["verified", "unknown", "malformed"], status
        ),
        opening_open=stop.get("opening_open"),
        opening_close=stop.get("opening_close"),
    )
    return ScheduledStop(
        place=place,
        score=float(stop.get("score") or 0.0),
        visit_duration_min=int(stop.get("visit_duration_min") or 60),
        suggested_start_time=str(stop.get("suggested_start_time") or "09:00"),
        arrival_note=stop.get("arrival_note"),
    )


def _stops_from_schedule_day(schedule_day: Any) -> list[ScheduledStop]:
    if schedule_day is None:
        return []
    # P6.0 day dict
    if isinstance(schedule_day, dict):
        raw_stops = schedule_day.get("stops") or []
        return [
            _scheduled_from_flat(s) if isinstance(s, dict) else s
            for s in raw_stops
        ]
    # Legacy list[stop]
    if isinstance(schedule_day, list):
        return [
            _scheduled_from_flat(s) if isinstance(s, dict) else s
            for s in schedule_day
        ]
    return []


def _day_plan(schedule_day: Any, route_day: dict | None) -> DayPlan:
    stops = _stops_from_schedule_day(schedule_day)
    total = 0
    dropped: list[DroppedStop] = []
    if isinstance(schedule_day, dict) and schedule_day.get("total_travel_min") is not None:
        total = int(schedule_day.get("total_travel_min") or 0)
    if isinstance(route_day, dict):
        if not total:
            total = int(route_day.get("total_travel_min") or 0)
        for d in route_day.get("dropped_stops") or []:
            dropped.append(
                DroppedStop.model_validate(d) if isinstance(d, dict) else d
            )
    return DayPlan(stops=stops, total_travel_min=total, dropped_stops=dropped)


def _search_area_args(state: Any) -> tuple[tuple[float, float] | None, float | None]:
    raw = state_get(state, "search_area")
    if not isinstance(raw, dict):
        return None, None
    radius = raw.get("radius_km")
    anchor = raw.get("anchor")
    if radius is None or not isinstance(anchor, dict):
        return None, None
    lat = anchor.get("lat")
    lng = anchor.get("lng")
    if lat is None or lng is None:
        return None, None
    try:
        return (float(lat), float(lng)), float(radius)
    except (TypeError, ValueError):
        return None, None


def _geometry_flags(route_day: dict) -> tuple[bool, bool]:
    legs = route_day.get("legs") or []
    any_fallback = False
    for leg in legs:
        if isinstance(leg, dict) and leg.get("used_fallback"):
            any_fallback = True
        elif getattr(leg, "used_fallback", False):
            any_fallback = True
    polyline = route_day.get("day_polyline")
    has_polyline = isinstance(polyline, str) and bool(polyline.strip())
    promised = bool(legs) and not any_fallback
    return promised, promised and not has_polyline


def _inter_stop_durations(stops: list[ScheduledStop], route_day: dict) -> list[int] | None:
    raw_legs = route_day.get("legs") or []
    if len(stops) < 2 or not raw_legs:
        return None
    legs: list[RouteLeg] = []
    for item in raw_legs:
        if isinstance(item, RouteLeg):
            legs.append(item)
        elif isinstance(item, dict):
            legs.append(RouteLeg.model_validate(item))
    lookup = legs_to_lookup(legs)
    durations: list[int] = []
    for left, right in zip(stops, stops[1:]):
        leg = lookup.get((left.place.id, right.place.id))
        if leg is None:
            return None
        durations.append(int(leg.duration_min))
    return durations


def _tool_result(result, findings, *, enforce: bool) -> ToolResult:
    blocking = any(item.blocks_publish for item in findings)
    ok = result.passed if not enforce else bool(result.passed) and not blocking
    if ok:
        message = None
        code = None
    elif result.errors:
        message = "; ".join(result.errors) or "validation failed"
        code = "validation_failed"
    else:
        codes = [item.code for item in findings if item.blocks_publish]
        message = "; ".join(codes) or "validation failed"
        code = "validation_failed"
    log.info(
        "validator_v2_findings",
        enforce=enforce,
        finding_codes=[item.code for item in findings],
    )
    return ToolResult(
        ok=ok,
        code=code,
        message=message,
        data={
            "validation_result": result.model_dump(mode="json"),
            "last_validate_ok": ok,
            "errors": result.errors,
            "warnings": result.warnings,
            "v2_findings": [item.model_dump(mode="json") for item in findings],
        },
    )


async def run(
    inp: ValidateItineraryIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = inp
    _ = ctx
    schedule = state_get(state, "schedule") or []
    route = state_get(state, "route") or []

    if not schedule and not route:
        result = validate_trip(TripItinerary(days=[]))
        return ToolResult(
            ok=False,
            code="validation_failed",
            message="empty_itinerary",
            data={
                "validation_result": result.model_dump(mode="json"),
                "last_validate_ok": False,
                "errors": result.errors,
                "warnings": result.warnings,
            },
        )

    days: list[DayPlan] = []
    promised: list[bool] = []
    missing: list[bool] = []
    leg_durations: list[list[int] | None] = []
    n = max(len(schedule), len(route))
    for i in range(n):
        sched_day = schedule[i] if i < len(schedule) else []
        route_day = route[i] if i < len(route) else {}
        if not isinstance(route_day, dict):
            route_day = {}
        plan = _day_plan(sched_day, route_day)
        days.append(plan)
        day_promised, day_missing = _geometry_flags(route_day)
        promised.append(day_promised)
        missing.append(day_missing)
        leg_durations.append(_inter_stop_durations(plan.stops, route_day))

    result = validate_trip(TripItinerary(days=days))
    center, radius = _search_area_args(state)
    findings = collect_findings(
        TripItinerary(days=days),
        search_center=center,
        search_radius_km=radius,
        geometry_promised=promised,
        geometry_missing=missing,
        leg_durations_min=leg_durations,
    )
    enforce = bool(get_settings().VALIDATOR_V2_ENFORCE)
    return _tool_result(result, findings, enforce=enforce)
