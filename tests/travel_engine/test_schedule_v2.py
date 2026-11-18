"""Row 4.5 schedule V2 proofs. Flag-off timing stays the legacy clock."""

from __future__ import annotations

from uuid import uuid4

from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.protocols import RouteLeg
from src.travel_engine.schedule_builder import build_day_schedule
from src.travel_engine.travel_rules import (
    BASE_SENTINEL_ID,
    MIN_TRAVEL_BUFFER_MIN,
    visit_duration_min,
)


def _scored(
    name: str,
    *,
    category: str = "attraction",
    status: str = "unknown",
    opening_open: str | None = None,
    opening_close: str | None = None,
) -> ScoredPlace:
    return ScoredPlace(
        place=PlaceCandidate(
            id=uuid4(),
            name=name,
            category=category,
            lat=27.0,
            lng=88.0,
            opening_hours_status=status,  # type: ignore[arg-type]
            opening_open=opening_open,
            opening_close=opening_close,
        ),
        score=1.0,
    )


def _legs(order: list[ScoredPlace], hop_min: int) -> list[RouteLeg]:
    legs: list[RouteLeg] = []
    prev = BASE_SENTINEL_ID
    for stop in order:
        legs.append(
            RouteLeg(
                from_place_id=prev,
                to_place_id=stop.place.id,
                duration_min=hop_min,
                distance_km=1.0,
            )
        )
        prev = stop.place.id
    return legs


def test_mode_off_matches_default_and_uses_leg_only() -> None:
    stops = [_scored("A"), _scored("B")]
    legs = _legs(stops, 20)
    default = build_day_schedule(stops, legs)
    explicit = build_day_schedule(stops, legs, v2_enabled=False)
    assert [item.suggested_start_time for item in default] == [
        item.suggested_start_time for item in explicit
    ]
    assert default[0].suggested_start_time == "08:20"


def test_v2_hop_adds_buffer() -> None:
    stops = [_scored("A"), _scored("B")]
    legs = _legs(stops, 20)
    timed = build_day_schedule(stops, legs, v2_enabled=True)
    visit = visit_duration_min("attraction")
    assert timed[0].suggested_start_time == "08:50"
    # 08:50 + visit + 20 + buffer
    end = (8 * 60 + 50) + visit
    second = end + 20 + MIN_TRAVEL_BUFFER_MIN
    hours, minutes = divmod(second, 60)
    assert timed[1].suggested_start_time == f"{hours:02d}:{minutes:02d}"
    starts = [item.suggested_start_time for item in timed]
    assert starts == sorted(starts)
    assert len(set(starts)) == len(starts)


def test_malformed_hours_do_not_claim_open() -> None:
    stop = _scored("A", status="malformed")
    timed = build_day_schedule([stop], _legs([stop], 5), v2_enabled=True)
    assert timed
    note = timed[0].arrival_note or ""
    assert "open" not in note.lower()


def test_empty_verified_window_is_not_an_open_visit() -> None:
    stop = _scored("Closed", status="verified", opening_open="00:00", opening_close="00:00")
    timed = build_day_schedule([stop], _legs([stop], 5), v2_enabled=True)
    assert timed == []


def test_unknown_hours_do_not_delay_or_claim_open() -> None:
    stop = _scored("A", opening_open="10:00", opening_close="18:00")
    timed = build_day_schedule([stop], _legs([stop], 5), v2_enabled=True)
    assert timed[0].suggested_start_time == "08:35"
    note = timed[0].arrival_note or ""
    assert "open" not in note.lower()


def test_verified_window_waits_until_open() -> None:
    stop = _scored(
        "A",
        status="verified",
        opening_open="10:00",
        opening_close="18:00",
    )
    timed = build_day_schedule([stop], _legs([stop], 5), v2_enabled=True)
    assert timed[0].suggested_start_time == "10:00"


def test_visit_past_day_end_is_omitted() -> None:
    first = _scored("Early", status="verified", opening_open="08:00", opening_close="18:00")
    late = _scored(
        "Late",
        category="trailhead",
        status="verified",
        opening_open="15:30",
        opening_close="18:00",
    )
    stops = [first, late]
    timed = build_day_schedule(stops, _legs(stops, 5), v2_enabled=True)
    names = [item.place.name for item in timed]
    assert "Late" not in names
    assert "Early" in names
    starts = [item.suggested_start_time for item in timed]
    assert starts == sorted(set(starts))


def test_preserve_order_ignores_v2_hour_shift() -> None:
    stops = [
        _scored("A"),
        _scored("B"),
        _scored("View", category="viewpoint", status="verified", opening_open="06:00", opening_close="07:00"),
    ]
    legacy = build_day_schedule(stops, _legs(stops, 10), preserve_order=True)
    both = build_day_schedule(
        stops, _legs(stops, 10), preserve_order=True, v2_enabled=True
    )
    assert [item.place.name for item in both] == [item.place.name for item in legacy]
    assert both[2].place.category == "viewpoint"
