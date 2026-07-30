"""Unit tests for travel_engine.day_allocator (step 4.4)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.travel_engine.day_allocator import allocate_days
from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.travel_rules import (
    ACTIVE_DAY_VISIT_BUDGET_MIN,
    MAX_PLACES_PER_DAY,
    visit_duration_min,
)


def _scored(
    name: str,
    *,
    category: str = "attraction",
    score: float = 1.0,
    lat: float = 27.0,
    lng: float = 88.0,
) -> ScoredPlace:
    return ScoredPlace(
        place=PlaceCandidate(
            id=uuid4(),
            name=name,
            category=category,
            enriched_tags=[],
            lat=lat,
            lng=lng,
        ),
        score=score,
        score_breakdown={},
    )


def test_eighteen_places_three_days_within_caps() -> None:
    selected = [
        _scored(f"P{i}", score=float(20 - i), lat=27.0 + i * 0.01, lng=88.0)
        for i in range(18)
    ]
    days = allocate_days(selected, 3)
    assert len(days) == 3
    assert all(len(d) <= MAX_PLACES_PER_DAY for d in days)
    for d in days:
        total = sum(visit_duration_min(s.place.category) for s in d)
        assert total <= ACTIVE_DAY_VISIT_BUDGET_MIN


def test_days_zero_raises_value_error() -> None:
    with pytest.raises(ValueError, match="days must be >= 1"):
        allocate_days([_scored("A")], 0)


def test_never_more_than_max_places_per_day() -> None:
    selected = [
        _scored(f"P{i}", score=float(30 - i), lat=27.0, lng=88.0) for i in range(20)
    ]
    days = allocate_days(selected, 2)
    assert all(len(d) <= MAX_PLACES_PER_DAY for d in days)


def test_trailhead_heavy_respects_visit_budget() -> None:
    # trailhead = 90 min; budget 450 → at most 5 trailheads per day
    selected = [
        _scored(f"T{i}", category="trailhead", score=float(20 - i), lat=27.0, lng=88.0)
        for i in range(12)
    ]
    days = allocate_days(selected, 2)
    for d in days:
        assert len(d) <= MAX_PLACES_PER_DAY
        total = sum(visit_duration_min(s.place.category) for s in d)
        assert total <= ACTIVE_DAY_VISIT_BUDGET_MIN
        assert total <= 5 * 90


def test_nearby_places_prefer_same_day() -> None:
    near_a = _scored("NearA", score=10.0, lat=27.04, lng=88.26)
    near_b = _scored("NearB", score=9.5, lat=27.041, lng=88.261)
    far = _scored("Far", score=9.0, lat=28.5, lng=90.0)  # well beyond 10 km
    days = allocate_days([near_a, near_b, far], 2)
    flat = {s.place.name: di for di, day in enumerate(days) for s in day}
    assert flat["NearA"] == flat["NearB"]
    assert flat["Far"] != flat["NearA"] or len([d for d in days if d]) == 1


def test_returns_exact_day_count_even_if_empty() -> None:
    days = allocate_days([], 4)
    assert len(days) == 4
    assert all(d == [] for d in days)
