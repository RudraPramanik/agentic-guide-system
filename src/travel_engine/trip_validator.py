"""Trip validator — chain-of-responsibility rule checks (pure, no I/O).

Geo coherence: per-day dispersion of stop coordinates in local km offsets from
the day's centroid — sqrt(sample_var(north_km) + sample_var(east_km)). Threshold
is GEO_COHERENCE_MAX_STDDEV_KM from travel_rules (never inlined). Days with fewer
than two stops are skipped.
"""

from __future__ import annotations

import math
from collections import Counter

from pydantic import BaseModel, Field

from src.travel_engine.route_optimizer import DroppedStop
from src.travel_engine.schedule_builder import ScheduledStop
from src.travel_engine.travel_rules import (
    ANCHOR_MIN_SCORE,
    GEO_COHERENCE_MAX_STDDEV_KM,
    MAX_DAILY_TRAVEL_MIN,
    MORNING_ONLY_CATEGORIES,
    MORNING_SLOT_LATEST_START,
)

_DROPPED_STOPS_WARNING = (
    "one_or_more_days_already_dropped_stops_prefer_expand_poi_search"
)


class ValidationResult(BaseModel):
    passed: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DayPlan(BaseModel):
    stops: list[ScheduledStop]
    total_travel_min: int
    dropped_stops: list[DroppedStop] = Field(default_factory=list)


class TripItinerary(BaseModel):
    days: list[DayPlan]


def _parse_hhmm(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _day_coord_stddev_km(stops: list[ScheduledStop]) -> float:
    """Coordinate dispersion (km): sqrt(s²_north + s²_east) about the centroid.

    Using distance-to-centroid sample std-dev would be 0 for any two-point day
    (equal radii). Axis sample variances in local km capture spread correctly.
    """
    n = len(stops)
    mean_lat = sum(s.place.lat for s in stops) / n
    mean_lng = sum(s.place.lng for s in stops) / n
    cos_lat = math.cos(math.radians(mean_lat))
    north = [(s.place.lat - mean_lat) * 111.0 for s in stops]
    east = [(s.place.lng - mean_lng) * 111.0 * cos_lat for s in stops]
    mean_n = sum(north) / n
    mean_e = sum(east) / n
    var_n = sum((x - mean_n) ** 2 for x in north) / (n - 1)
    var_e = sum((x - mean_e) ** 2 for x in east) / (n - 1)
    return math.sqrt(var_n + var_e)


def check_daily_travel_cap(itinerary: TripItinerary) -> list[str]:
    errors: list[str] = []
    for i, day in enumerate(itinerary.days):
        if day.total_travel_min > MAX_DAILY_TRAVEL_MIN:
            errors.append(
                f"day {i}: total_travel_min {day.total_travel_min} "
                f"exceeds daily travel cap {MAX_DAILY_TRAVEL_MIN}"
            )
    return errors


def check_no_repeat_places(itinerary: TripItinerary) -> list[str]:
    counts: Counter = Counter()
    names: dict = {}
    for day in itinerary.days:
        for stop in day.stops:
            pid = stop.place.id
            counts[pid] += 1
            names[pid] = stop.place.name
    errors: list[str] = []
    for pid, count in counts.items():
        if count > 1:
            errors.append(
                f"repeated place '{names[pid]}' (id={pid}) appears {count} times"
            )
    return errors


def check_morning_slots(itinerary: TripItinerary) -> list[str]:
    errors: list[str] = []
    latest = _parse_hhmm(MORNING_SLOT_LATEST_START)
    for day_i, day in enumerate(itinerary.days):
        for slot_i, stop in enumerate(day.stops):
            if stop.place.category not in MORNING_ONLY_CATEGORIES:
                continue
            order = slot_i + 1  # 1-based
            start_min = _parse_hhmm(stop.suggested_start_time)
            if order > 2 or start_min > latest:
                errors.append(
                    f"morning_slot_violation: day {day_i}: morning-only place "
                    f"'{stop.place.name}' in slot {order} starting "
                    f"{stop.suggested_start_time} "
                    f"(must be order ≤2 and start ≤ {MORNING_SLOT_LATEST_START})"
                )
    return errors


def check_anchor_per_day(itinerary: TripItinerary) -> list[str]:
    errors: list[str] = []
    for i, day in enumerate(itinerary.days):
        if not any(s.score > ANCHOR_MIN_SCORE for s in day.stops):
            errors.append(
                f"day {i}: no anchor stop with score > {ANCHOR_MIN_SCORE}"
            )
    return errors


def check_geo_coherence(itinerary: TripItinerary) -> list[str]:
    errors: list[str] = []
    for i, day in enumerate(itinerary.days):
        if len(day.stops) < 2:
            continue
        stddev = _day_coord_stddev_km(day.stops)
        if stddev > GEO_COHERENCE_MAX_STDDEV_KM:
            errors.append(
                f"day {i}: geo coherence stddev {stddev:.2f} km exceeds "
                f"{GEO_COHERENCE_MAX_STDDEV_KM}"
            )
    return errors


def validate_trip(itinerary: TripItinerary) -> ValidationResult:
    if not itinerary.days:
        return ValidationResult(
            passed=False,
            errors=["empty_itinerary"],
        )

    errors: list[str] = []
    for check in (
        check_daily_travel_cap,
        check_no_repeat_places,
        check_morning_slots,
        check_anchor_per_day,
        check_geo_coherence,
    ):
        errors.extend(check(itinerary))

    warnings: list[str] = []
    if any(d.dropped_stops for d in itinerary.days):
        warnings.append(_DROPPED_STOPS_WARNING)

    return ValidationResult(
        passed=not errors,
        warnings=warnings,
        errors=errors,
    )
