"""§11.6 property tests. They do not edit the travel engine."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from src.evaluation.metrics import geographic_coherence_km
from src.travel_engine.day_allocator import allocate_days
from src.travel_engine.place_selector import (
    PlaceCandidate,
    ScoredPlace,
    TripPreferences,
    select_places,
)
from src.travel_engine.protocols import RouteLeg
from src.travel_engine.schedule_builder import ScheduledStop, build_day_schedule
from src.travel_engine.travel_rules import (
    ACTIVE_DAY_VISIT_BUDGET_MIN,
    BASE_SENTINEL_ID,
    MAX_PLACES_PER_DAY,
    visit_duration_min,
)
from src.travel_engine.trip_validator import DayPlan, TripItinerary
from tests.travel_engine.fake_routing import FakeRoutingProvider

_ENGINE = Path(__file__).resolve().parents[2] / "src" / "travel_engine"


def _candidate(
    name: str,
    category: str,
    *,
    lat: float,
    lng: float,
    place_id: UUID,
    tags: list[str] | None = None,
) -> PlaceCandidate:
    return PlaceCandidate(
        id=place_id,
        name=name,
        category=category,
        enriched_tags=tags or [category],
        lat=lat,
        lng=lng,
    )


def _pair() -> tuple[list[PlaceCandidate], TripPreferences]:
    prefs = TripPreferences(interests=["museum", "park"], days=1)
    candidates = [
        _candidate(
            "Museum",
            "museum",
            lat=27.04,
            lng=88.26,
            place_id=UUID("00000000-0000-0000-0000-000000000101"),
        ),
        _candidate(
            "Park",
            "park",
            lat=27.041,
            lng=88.261,
            place_id=UUID("00000000-0000-0000-0000-000000000102"),
        ),
    ]
    return candidates, prefs


def _selected_ids(candidates: list[PlaceCandidate], prefs: TripPreferences) -> list[str]:
    return [str(item.place.id) for item in select_places(candidates, prefs)]


def _day_ids(candidates: list[PlaceCandidate], prefs: TripPreferences) -> list[list[str]]:
    selected = select_places(candidates, prefs)
    days = allocate_days(selected, prefs.days, prefs)
    return [[str(item.place.id) for item in day] for day in days]


def test_selection_is_deterministic() -> None:
    candidates, prefs = _pair()
    assert _selected_ids(candidates, prefs) == _selected_ids(candidates, prefs)
    assert _day_ids(candidates, prefs) == _day_ids(candidates, prefs)


def test_shuffled_input_keeps_selection_and_days() -> None:
    candidates, prefs = _pair()
    shuffled = list(reversed(candidates))
    assert _selected_ids(candidates, prefs) == _selected_ids(shuffled, prefs)
    assert _day_ids(candidates, prefs) == _day_ids(shuffled, prefs)


def test_removal_keeps_unique_ids_and_chronology() -> None:
    candidates, _prefs = _pair()
    stops = [
        ScheduledStop(
            place=candidates[0],
            score=1.0,
            visit_duration_min=40,
            suggested_start_time="09:00",
        ),
        ScheduledStop(
            place=candidates[1],
            score=1.0,
            visit_duration_min=30,
            suggested_start_time="10:00",
        ),
    ]
    TripItinerary(
        days=[DayPlan(stops=stops, total_travel_min=10)]
    )
    for index in range(len(stops)):
        remaining = [stop for position, stop in enumerate(stops) if position != index]
        ids = [stop.place.id for stop in remaining]
        assert len(ids) == len(set(ids))
        minutes = []
        for stop in remaining:
            hours, mins = stop.suggested_start_time.split(":")
            minutes.append(int(hours) * 60 + int(mins))
        assert minutes == sorted(minutes)


def test_distant_point_does_not_improve_coherence() -> None:
    candidates, prefs = _pair()
    selected = select_places(candidates, prefs)
    day = allocate_days(selected, 1, prefs)[0]
    coords = [(item.place.lat, item.place.lng) for item in day]
    before = geographic_coherence_km(coords)
    assert before is not None
    mean_lat = sum(lat for lat, _lng in coords) / len(coords)
    mean_lng = sum(lng for _lat, lng in coords) / len(coords)
    farther = geographic_coherence_km(coords + [(mean_lat + 1.0, mean_lng)])
    assert farther is not None
    assert farther >= before


def test_allocated_days_respect_caps() -> None:
    """Default allocator only. V2 mode is covered by its own feature tests."""
    candidates, prefs = _pair()
    selected = select_places(candidates, prefs)
    for day in allocate_days(selected, 1, prefs):
        assert len(day) <= MAX_PLACES_PER_DAY
        visit = sum(visit_duration_min(item.place.category) for item in day)
        assert visit <= ACTIVE_DAY_VISIT_BUDGET_MIN


@pytest.mark.asyncio
async def test_schedule_times_increase_and_match_leg() -> None:
    candidates, prefs = _pair()
    selected = select_places(candidates, prefs)
    provider = FakeRoutingProvider(default_duration_min=10, default_distance_km=1.0)
    waypoints = [(BASE_SENTINEL_ID, 27.03, 88.26)]
    waypoints.extend(
        (item.place.id, item.place.lat, item.place.lng) for item in selected
    )
    legs = await provider.travel_matrix(waypoints)
    schedule = build_day_schedule(selected, legs)
    starts = []
    for stop in schedule:
        hours, mins = stop.suggested_start_time.split(":")
        starts.append(int(hours) * 60 + int(mins))
    for earlier, later in zip(starts, starts[1:]):
        assert later > earlier
    if len(schedule) >= 2:
        gap = starts[1] - (starts[0] + schedule[0].visit_duration_min)
        hop = next(
            leg
            for leg in legs
            if isinstance(leg, RouteLeg)
            and leg.from_place_id == schedule[0].place.id
            and leg.to_place_id == schedule[1].place.id
        )
        assert gap == hop.duration_min


def test_engine_does_not_read_v2_flag() -> None:
    for path in sorted(_ENGINE.glob("*.py")):
        text = path.read_text(encoding="utf-8-sig")
        assert "TRAVEL_ENGINE_V2_ENABLED" not in text
        assert "VALIDATOR_V2_ENFORCE" not in text
        assert "get_settings" not in text


def test_injected_off_matches_legacy_scoring() -> None:
    prefs = TripPreferences(interests=["photography", "viewpoint"])
    place = _candidate(
        "Tiger Hill",
        "viewpoint",
        lat=27.04,
        lng=88.26,
        place_id=UUID("00000000-0000-4000-8000-0000000000aa"),
        tags=["photography", "viewpoint"],
    )
    legacy = select_places([place], prefs)
    off = select_places([place], prefs, v2_enabled=False)
    assert legacy[0].score == off[0].score
    assert legacy[0].score_breakdown == off[0].score_breakdown


def test_idempotent_dedup() -> None:
    from src.travel_engine.candidate_normalizer import normalize_candidates

    a = _candidate(
        "Ghoom Monastery",
        "monastery",
        lat=27.3300,
        lng=88.1300,
        place_id=UUID("00000000-0000-4000-8000-0000000000b1"),
    )
    b = _candidate(
        "ghoom monastery",
        "monastery",
        lat=27.3301,
        lng=88.1301,
        place_id=UUID("00000000-0000-4000-8000-0000000000b2"),
    )
    first = normalize_candidates([a, b])
    second = normalize_candidates(first)
    assert {c.id for c in first} == {c.id for c in second}


def test_area_respect() -> None:
    """Containment is pure; the engine package still does not import it."""
    from src.location_intelligence.containment import point_in_search_area
    from src.location_intelligence.schemas import (
        LocationType,
        ResolvedLocation,
        SearchArea,
    )

    anchor = ResolvedLocation(
        canonical_name="Center",
        location_type=LocationType.LANDMARK,
        lat=27.0,
        lng=88.0,
        provider="user",
        provider_id=None,
        confidence=1.0,
        explanation="fixture",
    )
    area = SearchArea(
        strategy="radius",
        anchor=anchor,
        radius_km=10.0,
        boundary_geojson=None,
        fallback_used=False,
        description="10 km",
    )
    assert point_in_search_area(27.01, 88.01, area) is True
    assert point_in_search_area(28.0, 89.0, area) is False

