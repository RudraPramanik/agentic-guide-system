"""Structured validation findings. Pure. Does not read settings or call tools.

G14 registry file is finding_codes.py, which re-exports FINDING_CODES.
"""

from __future__ import annotations

import math
import re
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from src.travel_engine.travel_rules import (
    ACTIVE_DAY_VISIT_BUDGET_MIN,
    ANCHOR_MIN_SCORE,
    BASE_SENTINEL_ID,
    MAX_DAILY_TRAVEL_MIN,
    MAX_PLACES_PER_DAY,
    visit_duration_min,
)
from src.travel_engine.trip_validator import (
    TripItinerary,
    check_anchor_per_day,
    check_daily_travel_cap,
    check_geo_coherence,
    check_morning_slots,
    check_no_repeat_places,
)

FINDING_CODES: tuple[str, ...] = (
    "DUPLICATE_STOP",
    "INVALID_COORDINATES",
    "MISSING_PLACE_ID",
    "OUT_OF_SEARCH_AREA",
    "EXCESSIVE_TRAVEL_TIME",
    "OVERLOADED_DAY",
    "OPENING_HOURS_CONFLICT",
    "OPENING_HOURS_UNKNOWN",
    "MISSING_ROUTE_GEOMETRY",
    "ROUTE_SCHEDULE_MISMATCH",
    "NON_CHRONOLOGICAL_SCHEDULE",
    "UNREALISTIC_VISIT_SEQUENCE",
    "INSUFFICIENT_EVIDENCE",
    "MORNING_ONLY_VIOLATION",
    "NO_ANCHOR_ATTRACTION",
    "GEO_INCOHERENT_DAY",
)

_DAY_INDEX = re.compile(r"day (\d+)")


class Severity(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationFinding(BaseModel):
    code: str
    severity: Severity
    day: int | None = None
    stop_ids: list[UUID] = Field(default_factory=list)
    message: str
    repairable: bool
    suggested_action: str | None = None
    blocks_publish: bool


# severity, blocks_publish, suggested_action
_RULES: dict[str, tuple[Severity, bool, str | None]] = {
    "DUPLICATE_STOP": (Severity.CRITICAL, True, "drop_weakest_stop"),
    "INVALID_COORDINATES": (Severity.CRITICAL, True, "drop_weakest_stop"),
    "MISSING_PLACE_ID": (Severity.CRITICAL, True, "drop_weakest_stop"),
    "OUT_OF_SEARCH_AREA": (Severity.CRITICAL, True, "drop_weakest_stop"),
    "EXCESSIVE_TRAVEL_TIME": (Severity.ERROR, False, "drop_weakest_stop"),
    "OVERLOADED_DAY": (Severity.ERROR, False, "drop_weakest_stop"),
    "OPENING_HOURS_CONFLICT": (Severity.CRITICAL, True, "reoptimize_routes"),
    "OPENING_HOURS_UNKNOWN": (Severity.INFO, False, None),
    "MISSING_ROUTE_GEOMETRY": (Severity.CRITICAL, True, "reoptimize_routes"),
    "ROUTE_SCHEDULE_MISMATCH": (Severity.CRITICAL, True, "reoptimize_routes"),
    "NON_CHRONOLOGICAL_SCHEDULE": (Severity.CRITICAL, True, "reoptimize_routes"),
    "UNREALISTIC_VISIT_SEQUENCE": (Severity.ERROR, False, "reoptimize_routes"),
    "INSUFFICIENT_EVIDENCE": (Severity.INFO, False, None),
    "MORNING_ONLY_VIOLATION": (Severity.ERROR, False, "reoptimize_routes"),
    "NO_ANCHOR_ATTRACTION": (Severity.ERROR, False, "expand_poi_search"),
    "GEO_INCOHERENT_DAY": (Severity.ERROR, False, "drop_weakest_stop"),
}


def make_finding(
    code: str,
    *,
    day: int | None,
    stop_ids: list[UUID],
    message: str,
) -> ValidationFinding:
    severity, blocks_publish, suggested_action = _RULES[code]
    return ValidationFinding(
        code=code,
        severity=severity,
        day=day,
        stop_ids=stop_ids,
        message=message,
        repairable=suggested_action is not None,
        suggested_action=suggested_action,
        blocks_publish=blocks_publish,
    )


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    arc = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(arc))


def _parse_hhmm(value: str) -> int | None:
    if ":" not in value:
        return None
    hours, minutes = value.split(":", 1)
    if not hours.isdigit() or not minutes.isdigit():
        return None
    return int(hours) * 60 + int(minutes)


def _days_in(errors: list[str]) -> set[int]:
    found: set[int] = set()
    for error in errors:
        match = _DAY_INDEX.search(error)
        if match:
            found.add(int(match.group(1)))
    return found


def _coords_invalid(lat: float, lng: float) -> bool:
    if not math.isfinite(lat) or not math.isfinite(lng):
        return True
    return lat < -90.0 or lat > 90.0 or lng < -180.0 or lng > 180.0


def collect_findings(
    itinerary: TripItinerary,
    *,
    search_center: tuple[float, float] | None = None,
    search_radius_km: float | None = None,
    geometry_promised: list[bool] | None = None,
    geometry_missing: list[bool] | None = None,
    leg_durations_min: list[list[int] | None] | None = None,
) -> list[ValidationFinding]:
    """V2 findings beside validate_trip. Does not change the string result."""
    findings: list[ValidationFinding] = []
    area_ready = search_center is not None and search_radius_km is not None
    center_lat = center_lng = 0.0
    radius_km = 0.0
    if area_ready and search_center is not None and search_radius_km is not None:
        center_lat, center_lng = search_center
        radius_km = float(search_radius_km)

    repeat_errors = check_no_repeat_places(itinerary)
    if repeat_errors:
        counts: dict[UUID, int] = {}
        for day in itinerary.days:
            for stop in day.stops:
                counts[stop.place.id] = counts.get(stop.place.id, 0) + 1
        for place_id, count in counts.items():
            if count > 1:
                findings.append(
                    make_finding(
                        "DUPLICATE_STOP",
                        day=None,
                        stop_ids=[place_id],
                        message=f"place {place_id} repeats {count} times",
                    )
                )

    cap_days = _days_in(check_daily_travel_cap(itinerary))
    morning_days = _days_in(check_morning_slots(itinerary))
    anchor_days = _days_in(check_anchor_per_day(itinerary))
    geo_days = _days_in(check_geo_coherence(itinerary))

    for index, day in enumerate(itinerary.days):
        stop_ids = [stop.place.id for stop in day.stops]
        if index in cap_days or day.total_travel_min > MAX_DAILY_TRAVEL_MIN:
            findings.append(
                make_finding(
                    "EXCESSIVE_TRAVEL_TIME",
                    day=index,
                    stop_ids=stop_ids,
                    message=(
                        f"day {index} travel {day.total_travel_min} "
                        f"exceeds {MAX_DAILY_TRAVEL_MIN}"
                    ),
                )
            )
        visit_sum = sum(visit_duration_min(stop.place.category) for stop in day.stops)
        if len(day.stops) > MAX_PLACES_PER_DAY or visit_sum > ACTIVE_DAY_VISIT_BUDGET_MIN:
            findings.append(
                make_finding(
                    "OVERLOADED_DAY",
                    day=index,
                    stop_ids=stop_ids,
                    message=f"day {index} exceeds place or visit cap",
                )
            )
        if index in morning_days:
            findings.append(
                make_finding(
                    "MORNING_ONLY_VIOLATION",
                    day=index,
                    stop_ids=stop_ids,
                    message=f"day {index} morning-only slot violation",
                )
            )
        if index in anchor_days:
            findings.append(
                make_finding(
                    "NO_ANCHOR_ATTRACTION",
                    day=index,
                    stop_ids=stop_ids,
                    message=f"day {index} has no anchor above {ANCHOR_MIN_SCORE}",
                )
            )
        if index in geo_days:
            findings.append(
                make_finding(
                    "GEO_INCOHERENT_DAY",
                    day=index,
                    stop_ids=stop_ids,
                    message=f"day {index} is geo-incoherent",
                )
            )
        promised = bool(geometry_promised[index]) if geometry_promised and index < len(geometry_promised) else False
        missing = bool(geometry_missing[index]) if geometry_missing and index < len(geometry_missing) else False
        if promised and missing:
            findings.append(
                make_finding(
                    "MISSING_ROUTE_GEOMETRY",
                    day=index,
                    stop_ids=stop_ids,
                    message=f"day {index} promised route geometry is missing",
                )
            )

        starts: list[int] = []
        chronological = True
        previous: int | None = None
        for stop in day.stops:
            parsed = _parse_hhmm(stop.suggested_start_time)
            if parsed is None or (previous is not None and parsed <= previous):
                chronological = False
            if parsed is not None:
                starts.append(parsed)
                previous = parsed
            if stop.place.id == BASE_SENTINEL_ID:
                findings.append(
                    make_finding(
                        "MISSING_PLACE_ID",
                        day=index,
                        stop_ids=[stop.place.id],
                        message="stop uses the base sentinel as its place id",
                    )
                )
            if _coords_invalid(stop.place.lat, stop.place.lng):
                findings.append(
                    make_finding(
                        "INVALID_COORDINATES",
                        day=index,
                        stop_ids=[stop.place.id],
                        message=f"invalid coordinates for {stop.place.id}",
                    )
                )
            if area_ready:
                distance = _haversine_km(
                    stop.place.lat, stop.place.lng, center_lat, center_lng
                )
                if distance > radius_km:
                    findings.append(
                        make_finding(
                            "OUT_OF_SEARCH_AREA",
                            day=index,
                            stop_ids=[stop.place.id],
                            message=f"{stop.place.id} is outside the supplied radius",
                        )
                    )
            if stop.place.evidence_count == 0:
                findings.append(
                    make_finding(
                        "INSUFFICIENT_EVIDENCE",
                        day=index,
                        stop_ids=[stop.place.id],
                        message=f"{stop.place.id} has no evidence",
                    )
                )
            status = stop.place.opening_hours_status
            open_min = _parse_hhmm(stop.place.opening_open or "")
            close_min = _parse_hhmm(stop.place.opening_close or "")
            start_min = _parse_hhmm(stop.suggested_start_time)
            verified = status == "verified" and open_min is not None and close_min is not None
            if verified and start_min is not None:
                end_min = start_min + stop.visit_duration_min
                if start_min < open_min or end_min > close_min:
                    findings.append(
                        make_finding(
                            "OPENING_HOURS_CONFLICT",
                            day=index,
                            stop_ids=[stop.place.id],
                            message=f"{stop.place.id} falls outside verified hours",
                        )
                    )
            else:
                findings.append(
                    make_finding(
                        "OPENING_HOURS_UNKNOWN",
                        day=index,
                        stop_ids=[stop.place.id],
                        message=f"{stop.place.id} hours are not verified",
                    )
                )

        if not chronological and len(day.stops) >= 2:
            findings.append(
                make_finding(
                    "NON_CHRONOLOGICAL_SCHEDULE",
                    day=index,
                    stop_ids=stop_ids,
                    message=f"day {index} start times are not strictly increasing",
                )
            )
        elif chronological and len(starts) >= 2:
            for left, right, left_stop in zip(starts, starts[1:], day.stops):
                if right < left + left_stop.visit_duration_min:
                    findings.append(
                        make_finding(
                            "UNREALISTIC_VISIT_SEQUENCE",
                            day=index,
                            stop_ids=stop_ids,
                            message=f"day {index} visits overlap",
                        )
                    )
                    break

        durations = None
        if leg_durations_min is not None and index < len(leg_durations_min):
            durations = leg_durations_min[index]
        if durations is not None and chronological and len(day.stops) >= 2:
            for hop, left_stop, right_stop in zip(durations, day.stops, day.stops[1:]):
                left_start = _parse_hhmm(left_stop.suggested_start_time)
                right_start = _parse_hhmm(right_stop.suggested_start_time)
                if left_start is None or right_start is None:
                    continue
                gap = right_start - (left_start + left_stop.visit_duration_min)
                if gap < hop:
                    findings.append(
                        make_finding(
                            "ROUTE_SCHEDULE_MISMATCH",
                            day=index,
                            stop_ids=stop_ids,
                            message=f"day {index} schedule gap is shorter than the leg",
                        )
                    )
                    break

    return findings
