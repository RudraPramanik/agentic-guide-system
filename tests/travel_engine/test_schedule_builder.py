"""Tests for travel_engine.schedule_builder."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.protocols import RouteLeg
from src.travel_engine.schedule_builder import build_day_schedule
from src.travel_engine.travel_rules import BASE_SENTINEL_ID, DAY_START_TIME


def _scored(
    name: str,
    *,
    category: str = "attraction",
    score: float = 1.0,
    place_id: UUID | None = None,
) -> ScoredPlace:
    return ScoredPlace(
        place=PlaceCandidate(
            id=place_id or uuid4(),
            name=name,
            category=category,
            enriched_tags=[],
            lat=0.0,
            lng=0.0,
        ),
        score=score,
        score_breakdown={},
    )


def _consecutive_legs(order: list[ScoredPlace], hop_min: int = 10) -> list[RouteLeg]:
    """base→first, then each consecutive hop (incomplete for morning reorder)."""
    legs: list[RouteLeg] = []
    prev = BASE_SENTINEL_ID
    for s in order:
        legs.append(
            RouteLeg(
                from_place_id=prev,
                to_place_id=s.place.id,
                duration_min=hop_min,
                distance_km=1.0,
            )
        )
        prev = s.place.id
    return legs


def _pairwise_legs(order: list[ScoredPlace], hop_min: int = 10) -> list[RouteLeg]:
    """Full directed pairwise among BASE + stops (for morning extract reorder)."""
    ids = [BASE_SENTINEL_ID, *[s.place.id for s in order]]
    legs: list[RouteLeg] = []
    for a in ids:
        for b in ids:
            if a == b:
                continue
            legs.append(
                RouteLeg(
                    from_place_id=a,
                    to_place_id=b,
                    duration_min=hop_min,
                    distance_km=1.0,
                )
            )
    return legs


def test_empty_stops():
    assert build_day_schedule([], []) == []


def test_six_stop_day_starts_from_day_start():
    stops = [_scored(f"S{i}") for i in range(6)]
    legs = _consecutive_legs(stops, hop_min=5)
    schedule = build_day_schedule(stops, legs)
    assert len(schedule) == 6
    assert all(s.suggested_start_time for s in schedule)
    assert schedule[0].suggested_start_time >= DAY_START_TIME
    # base travel 5 min → first start 08:05
    assert schedule[0].suggested_start_time == "08:05"


def test_viewpoint_lands_in_morning_slot():
    late_view = _scored("Tiger Hill", category="viewpoint", score=2.0)
    early = _scored("Museum", category="museum", score=1.0)
    mid = _scored("Park", category="park", score=1.0)
    # Input order has viewpoint last; pairwise legs allow morning extract
    stops = [early, mid, late_view]
    schedule = build_day_schedule(stops, _pairwise_legs(stops, hop_min=5))
    assert schedule[0].place.name == "Tiger Hill"
    assert schedule[0].place.category == "viewpoint"
    assert schedule[0].suggested_start_time <= "10:30"


def test_lunch_gap_when_spanning_lunch():
    # Long visits so the day crosses 13:00
    stops = [
        _scored("A", category="trailhead"),  # 90
        _scored("B", category="museum"),  # 60
        _scored("C", category="museum"),  # 60
        _scored("D", category="museum"),  # 60
    ]
    legs = _consecutive_legs(stops, hop_min=30)
    schedule = build_day_schedule(stops, legs)
    notes = [s.arrival_note for s in schedule if s.arrival_note]
    assert any(n and "lunch" in n for n in notes)
    # After lunch insertion, some stop should start at/after 13:00 + buffer path
    assert any(s.suggested_start_time >= "13:00" for s in schedule)


def test_too_few_legs_raises():
    stops = [_scored("A"), _scored("B")]
    with pytest.raises(ValueError, match="incompatible"):
        build_day_schedule(stops, [])


def test_missing_hop_after_morning_extract_raises():
    view = _scored("View", category="viewpoint")
    other = _scored("Other", category="museum")
    # Consecutive legs for [other, view] only — extract puts view first,
    # needing BASE→view which is missing.
    legs = _consecutive_legs([other, view], hop_min=10)
    with pytest.raises(ValueError, match="missing route leg"):
        build_day_schedule([other, view], legs)
