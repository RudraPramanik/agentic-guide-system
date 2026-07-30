"""validate_itinerary — VALIDATE; map state → TripItinerary → validate_trip."""

from __future__ import annotations

from typing import Any

from src.planner.tools._helpers import state_get
from src.planner.tools.schemas import ToolResult, ValidateItineraryIn
from src.travel_engine.route_optimizer import DroppedStop
from src.travel_engine.schedule_builder import ScheduledStop
from src.travel_engine.trip_validator import DayPlan, TripItinerary, validate_trip


def _day_plan(schedule_day: list, route_day: dict | None) -> DayPlan:
    stops = [
        ScheduledStop.model_validate(s) if isinstance(s, dict) else s
        for s in (schedule_day or [])
    ]
    total = 0
    dropped: list[DroppedStop] = []
    if isinstance(route_day, dict):
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
        days.append(_day_plan(sched_day, route_day if isinstance(route_day, dict) else {}))

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
