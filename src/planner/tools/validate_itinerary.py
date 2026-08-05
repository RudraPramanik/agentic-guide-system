"""validate_itinerary — VALIDATE; map state → TripItinerary → validate_trip."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.planner.tools._helpers import state_get
from src.planner.tools.schemas import ToolResult, ValidateItineraryIn
from src.travel_engine.place_selector import PlaceCandidate
from src.travel_engine.route_optimizer import DroppedStop
from src.travel_engine.schedule_builder import ScheduledStop
from src.travel_engine.trip_validator import DayPlan, TripItinerary, validate_trip


def _as_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _scheduled_from_flat(stop: dict) -> ScheduledStop:
    """Rebuild ScheduledStop from P6.0 flat stop dict (or nested legacy dump)."""
    if "place" in stop and isinstance(stop["place"], dict):
        return ScheduledStop.model_validate(stop)
    place = PlaceCandidate(
        id=_as_uuid(stop["place_id"]),
        name=str(stop.get("name") or ""),
        category=str(stop.get("category") or "attraction"),
        enriched_tags=list(stop.get("enriched_tags") or []),
        lat=float(stop.get("lat") or 0.0),
        lng=float(stop.get("lng") or 0.0),
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
    n = max(len(schedule), len(route))
    for i in range(n):
        sched_day = schedule[i] if i < len(schedule) else []
        route_day = route[i] if i < len(route) else {}
        days.append(
            _day_plan(sched_day, route_day if isinstance(route_day, dict) else {})
        )

    result = validate_trip(TripItinerary(days=days))
    return ToolResult(
        ok=result.passed,
        code=None if result.passed else "validation_failed",
        message=None if result.passed else "; ".join(result.errors) or "validation failed",
        data={
            "validation_result": result.model_dump(mode="json"),
            "last_validate_ok": result.passed,
            "errors": result.errors,
            "warnings": result.warnings,
        },
    )
