"""Day schedule builder — naive wall-clock start times (pure, no I/O).

Morning-only algorithm (before first timing):
1. If any stop's structural category is in MORNING_ONLY_CATEGORIES, stable-extract
   morning-only stops to the front (preserve relative order among morning-only
   and among others).
2. Place k = min(2, n_morning) morning-only stops in the earliest slots.
3. Time the day using legs_to_lookup; missing required hops after extract raise
   ValueError (do not invent durations; do not call geo).

Times are destination-local naive "HH:MM" strings — never timezone / UTC.
Lunch: insert LUNCH_BREAK_MIN when the next visit would cross LUNCH_BREAK_START.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.protocols import RouteLeg, legs_to_lookup
from src.travel_engine.travel_rules import (
    BASE_SENTINEL_ID,
    DAY_START_TIME,
    LUNCH_BREAK_MIN,
    LUNCH_BREAK_START,
    MORNING_ONLY_CATEGORIES,
    visit_duration_min,
)


class ScheduledStop(BaseModel):
    place: PlaceCandidate
    score: float
    visit_duration_min: int
    suggested_start_time: str  # "HH:MM"
    arrival_note: str | None = None


def _parse_hhmm(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _format_hhmm(total_min: int) -> str:
    total_min = max(0, total_min) % (24 * 60)
    return f"{total_min // 60:02d}:{total_min % 60:02d}"


def _extract_morning_first(stops: list[ScoredPlace]) -> list[ScoredPlace]:
    morning = [
        s for s in stops if s.place.category in MORNING_ONLY_CATEGORIES
    ]
    if not morning:
        return list(stops)
    others = [
        s for s in stops if s.place.category not in MORNING_ONLY_CATEGORIES
    ]
    k = min(2, len(morning))
    early = morning[:k]
    rest_morning = morning[k:]
    return early + rest_morning + others


def _required_hops(order: list[ScoredPlace]) -> list[tuple[UUID, UUID]]:
    if not order:
        return []
    hops = [(BASE_SENTINEL_ID, order[0].place.id)]
    for i in range(len(order) - 1):
        hops.append((order[i].place.id, order[i + 1].place.id))
    return hops


def _hop_duration(
    lookup: dict[tuple[UUID, UUID], RouteLeg],
    frm: UUID,
    to: UUID,
) -> int:
    leg = lookup.get((frm, to))
    if leg is None:
        raise ValueError(f"missing route leg for {frm} -> {to}")
    return leg.duration_min


def build_day_schedule(
    ordered_stops: list[ScoredPlace],
    route_legs: list[RouteLeg],
) -> list[ScheduledStop]:
    """
    Assign naive suggested_start_time for each stop.

    Common path: len(route_legs) == len(ordered_stops) consecutive chain
    (base→first, …). Larger lists are treated as lookup-complete.
    """
    if not ordered_stops:
        return []

    if len(route_legs) < len(ordered_stops):
        raise ValueError(
            f"route_legs length {len(route_legs)} incompatible with "
            f"{len(ordered_stops)} stops (need at least one consecutive chain)"
        )

    lookup = legs_to_lookup(route_legs)
    order = _extract_morning_first(ordered_stops)

    for frm, to in _required_hops(order):
        if (frm, to) not in lookup:
            raise ValueError(f"missing route leg for {frm} -> {to}")

    lunch_start = _parse_hhmm(LUNCH_BREAK_START)
    clock = _parse_hhmm(DAY_START_TIME)
    # Travel from base to first before first visit starts
    clock += _hop_duration(lookup, BASE_SENTINEL_ID, order[0].place.id)

    lunch_taken = False
    scheduled: list[ScheduledStop] = []

    for i, scored in enumerate(order):
        visit = visit_duration_min(scored.place.category)
        note: str | None = None

        # If starting this visit would cross lunch without having taken it,
        # insert the lunch gap first.
        if not lunch_taken and clock < lunch_start < clock + visit:
            clock = lunch_start + LUNCH_BREAK_MIN
            lunch_taken = True
            note = "lunch break before visit"
        elif not lunch_taken and clock >= lunch_start:
            clock += LUNCH_BREAK_MIN
            lunch_taken = True
            note = "lunch break before visit"

        start = clock
        scheduled.append(
            ScheduledStop(
                place=scored.place,
                score=scored.score,
                visit_duration_min=visit,
                suggested_start_time=_format_hhmm(start),
                arrival_note=note,
            )
        )
        clock = start + visit

        if i + 1 < len(order):
            travel = _hop_duration(
                lookup, scored.place.id, order[i + 1].place.id
            )
            next_arrival = clock + travel
            # Crossing lunch during travel / before next visit
            if (
                not lunch_taken
                and clock < lunch_start <= next_arrival
            ):
                clock = lunch_start + LUNCH_BREAK_MIN
                lunch_taken = True
            else:
                clock = next_arrival

    return scheduled
