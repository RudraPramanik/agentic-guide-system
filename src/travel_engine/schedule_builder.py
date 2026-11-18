"""Day schedule builder — naive wall-clock start times (pure, no I/O).

Morning-only algorithm (before first timing):
1. If any stop's structural category is in MORNING_ONLY_CATEGORIES, stable-extract
   morning-only stops toward the front (preserve relative order among morning-only
   and among others).
2. Place k = min(2, n_morning) morning-only stops in the earliest slots; omit any
   excess morning-only beyond two from the timed day (allocator should already
   have capped; this is a safety net so slot 3+ morning validation cannot fire).
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
    DAY_END_TIME,
    DAY_START_TIME,
    LUNCH_BREAK_MIN,
    LUNCH_BREAK_START,
    MIN_TRAVEL_BUFFER_MIN,
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
    """Put up to two morning-only stops first; omit any excess morning-only."""
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
    # Excess morning-only (morning[k:]) omitted — do not leave in slot 3+.
    return early + others


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


def _claims_open(note: str | None) -> bool:
    if not note:
        return False
    return "open" in note.lower()


def _window_minutes(value: str | None) -> int | None:
    if not value or ":" not in value:
        return None
    hours, minutes = value.split(":", 1)
    if not hours.isdigit() or not minutes.isdigit():
        return None
    return int(hours) * 60 + int(minutes)


def _time_legacy(
    order: list[ScoredPlace],
    lookup: dict[tuple[UUID, UUID], RouteLeg],
) -> list[ScheduledStop]:
    """Current clock. Hop minutes are the leg duration only."""
    lunch_start = _parse_hhmm(LUNCH_BREAK_START)
    clock = _parse_hhmm(DAY_START_TIME)
    clock += _hop_duration(lookup, BASE_SENTINEL_ID, order[0].place.id)

    lunch_taken = False
    scheduled: list[ScheduledStop] = []

    for i, scored in enumerate(order):
        visit = visit_duration_min(scored.place.category)
        note: str | None = None

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
            travel = _hop_duration(lookup, scored.place.id, order[i + 1].place.id)
            next_arrival = clock + travel
            if not lunch_taken and clock < lunch_start <= next_arrival:
                clock = lunch_start + LUNCH_BREAK_MIN
                lunch_taken = True
            else:
                clock = next_arrival

    return scheduled


def _preview_v2(
    clock: int,
    lunch_taken: bool,
    travel: int,
    visit: int,
) -> tuple[int, int, str | None, bool]:
    """Return start, end, note, and whether lunch is taken after this stop."""
    lunch_start = _parse_hhmm(LUNCH_BREAK_START)
    note: str | None = None
    lunch = lunch_taken
    next_arrival = clock + travel
    if not lunch and clock < lunch_start <= next_arrival:
        cursor = lunch_start + LUNCH_BREAK_MIN
        lunch = True
    else:
        cursor = next_arrival
    if not lunch and cursor < lunch_start < cursor + visit:
        cursor = lunch_start + LUNCH_BREAK_MIN
        lunch = True
        note = "lunch break before visit"
    elif not lunch and cursor >= lunch_start:
        cursor = cursor + LUNCH_BREAK_MIN
        lunch = True
        note = "lunch break before visit"
    return cursor, cursor + visit, note, lunch


def _time_v2(
    order: list[ScoredPlace],
    lookup: dict[tuple[UUID, UUID], RouteLeg],
) -> list[ScheduledStop]:
    """Real leg minutes plus one buffer. Verified hours only. Naive clock."""
    day_end = _parse_hhmm(DAY_END_TIME)
    clock = _parse_hhmm(DAY_START_TIME)
    lunch_taken = False
    last_id = BASE_SENTINEL_ID
    scheduled: list[ScheduledStop] = []

    for scored in order:
        travel = _hop_duration(lookup, last_id, scored.place.id) + MIN_TRAVEL_BUFFER_MIN
        visit = visit_duration_min(scored.place.category)
        start, end, note, lunch_after = _preview_v2(clock, lunch_taken, travel, visit)
        place = scored.place
        verified = (
            place.opening_hours_status == "verified"
            and _window_minutes(place.opening_open) is not None
            and _window_minutes(place.opening_close) is not None
        )
        if verified:
            open_min = _window_minutes(place.opening_open)
            close_min = _window_minutes(place.opening_close)
            assert open_min is not None and close_min is not None
            if start < open_min:
                start = open_min
                end = start + visit
                note = None
            if end > close_min or end > day_end:
                continue
        else:
            if end > day_end:
                continue
            if _claims_open(note):
                note = None
        scheduled.append(
            ScheduledStop(
                place=place,
                score=scored.score,
                visit_duration_min=visit,
                suggested_start_time=_format_hhmm(start),
                arrival_note=note,
            )
        )
        clock = end
        lunch_taken = lunch_after
        last_id = place.id

    return scheduled


def build_day_schedule(
    ordered_stops: list[ScoredPlace],
    route_legs: list[RouteLeg],
    *,
    preserve_order: bool = False,
    v2_enabled: bool = False,
) -> list[ScheduledStop]:
    """
    Assign naive suggested_start_time for each stop.

    Common path: len(route_legs) == len(ordered_stops) consecutive chain
    (base→first, …). Larger lists are treated as lookup-complete.

    When preserve_order=True (P7 reorder), skip morning-only extract/omit and
    time stops in the given order. That path ignores V2 omission and hour waits.
    Default False keeps generation behavior. v2_enabled defaults false and
    must be injected by the caller; this module does not read settings.
    """
    if not ordered_stops:
        return []

    if len(route_legs) < len(ordered_stops):
        raise ValueError(
            f"route_legs length {len(route_legs)} incompatible with "
            f"{len(ordered_stops)} stops (need at least one consecutive chain)"
        )

    lookup = legs_to_lookup(route_legs)
    order = (
        list(ordered_stops)
        if preserve_order
        else _extract_morning_first(ordered_stops)
    )

    for frm, to in _required_hops(order):
        if (frm, to) not in lookup:
            raise ValueError(f"missing route leg for {frm} -> {to}")

    if preserve_order or not v2_enabled:
        return _time_legacy(order, lookup)
    return _time_v2(order, lookup)
