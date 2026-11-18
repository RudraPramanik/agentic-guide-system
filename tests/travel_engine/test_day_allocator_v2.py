"""Row 4.3 allocator proofs. Comparison found no cap miss, so modes match."""

from __future__ import annotations

from uuid import uuid4

from src.evaluation.metrics import geographic_coherence_km
from src.travel_engine.day_allocator import allocate_days
from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.travel_rules import (
    ACTIVE_DAY_VISIT_BUDGET_MIN,
    MAX_PLACES_PER_DAY,
    MORNING_ONLY_CATEGORIES,
    visit_duration_min,
)


def _scored(
    name: str,
    *,
    lat: float,
    lng: float,
    score: float = 1.0,
    category: str = "attraction",
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
    )


def _ids(days: list[list[ScoredPlace]]) -> list[list[str]]:
    return [[str(item.place.id) for item in day] for day in days]


def test_default_call_matches_explicit_mode_off() -> None:
    places = [
        _scored("Near", lat=27.03, lng=88.26, score=2.0),
        _scored("Also", lat=27.031, lng=88.261, score=1.5),
        _scored("Far", lat=27.20, lng=88.26, score=1.2),
    ]
    assert _ids(allocate_days(places, 2)) == _ids(
        allocate_days(places, 2, v2_enabled=False)
    )


def test_v2_matches_mode_off_when_comparison_has_no_miss() -> None:
    places = [
        _scored(f"P{i}", lat=27.03 + i * 0.01, lng=88.26, score=float(10 - i))
        for i in range(8)
    ]
    assert _ids(allocate_days(places, 3, v2_enabled=False)) == _ids(
        allocate_days(places, 3, v2_enabled=True)
    )


def test_far_cluster_does_not_join_a_near_day() -> None:
    near = _scored("Near", lat=27.03, lng=88.26, score=3.0)
    far = _scored("Far", lat=27.03, lng=88.50, score=2.0)
    days = allocate_days([near, far], 2, v2_enabled=True)
    near_days = [index for index, day in enumerate(days) if near in day]
    far_days = [index for index, day in enumerate(days) if far in day]
    assert near_days and far_days
    assert near_days[0] != far_days[0]


def test_v2_days_stay_inside_caps() -> None:
    places = [
        _scored(f"P{i}", lat=27.0 + (i % 3) * 0.2, lng=88.0, score=float(20 - i))
        for i in range(18)
    ]
    days = allocate_days(places, 3, v2_enabled=True)
    assert len(days) == 3
    for day in days:
        assert len(day) <= MAX_PLACES_PER_DAY
        visit = sum(visit_duration_min(item.place.category) for item in day)
        assert visit <= ACTIVE_DAY_VISIT_BUDGET_MIN
        morning = sum(
            1 for item in day if item.place.category in MORNING_ONLY_CATEGORIES
        )
        assert morning <= 2


def test_v2_coherence_is_not_worse() -> None:
    places = [
        _scored(f"P{i}", lat=27.03 + i * 0.01, lng=88.26, score=float(8 - i))
        for i in range(6)
    ]
    off = allocate_days(places, 2, v2_enabled=False)
    on = allocate_days(places, 2, v2_enabled=True)

    def _km(days: list[list[ScoredPlace]]) -> float:
        scores: list[float] = []
        for day in days:
            value = geographic_coherence_km(
                [(item.place.lat, item.place.lng) for item in day]
            )
            if value is not None:
                scores.append(value)
        return max(scores) if scores else 0.0

    assert _km(on) <= _km(off)
