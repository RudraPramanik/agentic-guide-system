"""Tests for travel_engine.trip_validator."""

from __future__ import annotations

from uuid import UUID, uuid4

from src.travel_engine.place_selector import PlaceCandidate
from src.travel_engine.route_optimizer import DroppedStop
from src.travel_engine.schedule_builder import ScheduledStop
from src.travel_engine.travel_rules import (
    ANCHOR_MIN_SCORE,
    GEO_COHERENCE_MAX_STDDEV_KM,
    MAX_DAILY_TRAVEL_MIN,
)
from src.travel_engine.trip_validator import (
    DayPlan,
    TripItinerary,
    validate_trip,
)

_WARNING = "one_or_more_days_already_dropped_stops_prefer_expand_poi_search"


def _stop(
    name: str,
    *,
    category: str = "attraction",
    score: float = 1.0,
    start: str = "08:00",
    lat: float = 27.04,
    lng: float = 88.26,
    place_id: UUID | None = None,
) -> ScheduledStop:
    return ScheduledStop(
        place=PlaceCandidate(
            id=place_id or uuid4(),
            name=name,
            category=category,
            enriched_tags=[],
            lat=lat,
            lng=lng,
        ),
        score=score,
        visit_duration_min=40,
        suggested_start_time=start,
    )


def _good_day(**kwargs) -> DayPlan:
    stops = kwargs.pop("stops", None)
    if stops is None:
        stops = [
            _stop("A", score=1.0, start="08:00", lat=27.04, lng=88.26),
            _stop("B", score=0.9, start="09:00", lat=27.05, lng=88.27),
        ]
    return DayPlan(
        stops=stops,
        total_travel_min=kwargs.pop("total_travel_min", 60),
        dropped_stops=kwargs.pop("dropped_stops", []),
    )


def test_good_itinerary_passes():
    result = validate_trip(TripItinerary(days=[_good_day()]))
    assert result.passed is True
    assert result.errors == []


def test_empty_itinerary():
    result = validate_trip(TripItinerary(days=[]))
    assert result.passed is False
    assert "empty_itinerary" in result.errors


def test_repeat_place_error():
    pid = uuid4()
    day = _good_day(
        stops=[
            _stop("A", score=1.0, place_id=pid, lat=27.04, lng=88.26),
            _stop("A-again", score=0.9, place_id=pid, lat=27.05, lng=88.27),
        ]
    )
    result = validate_trip(TripItinerary(days=[day]))
    assert result.passed is False
    assert any("repeated place" in e for e in result.errors)


def test_late_morning_viewpoint_error():
    day = _good_day(
        stops=[
            _stop("Museum", category="museum", score=1.0, start="08:00"),
            _stop("Park", category="park", score=0.9, start="09:00"),
            _stop(
                "LateView",
                category="viewpoint",
                score=0.95,
                start="11:00",
            ),
        ]
    )
    result = validate_trip(TripItinerary(days=[day]))
    assert result.passed is False
    assert any("morning-only" in e for e in result.errors)
    assert any(e.startswith("morning_slot_violation: ") for e in result.errors)


def test_no_anchor_error():
    day = _good_day(
        stops=[
            _stop("Weak1", score=ANCHOR_MIN_SCORE, lat=27.04, lng=88.26),
            _stop("Weak2", score=0.1, lat=27.05, lng=88.27),
        ]
    )
    result = validate_trip(TripItinerary(days=[day]))
    assert result.passed is False
    assert any("no anchor" in e for e in result.errors)


def test_over_travel_cap_error():
    day = _good_day(total_travel_min=MAX_DAILY_TRAVEL_MIN + 1)
    result = validate_trip(TripItinerary(days=[day]))
    assert result.passed is False
    assert any("daily travel cap" in e for e in result.errors)


def test_geo_coherence_error():
    # ~1° lat ≈ 111 km — far beyond GEO_COHERENCE_MAX_STDDEV_KM (15)
    day = _good_day(
        stops=[
            _stop("Near", score=1.0, lat=27.0, lng=88.0),
            _stop("Far", score=0.9, lat=27.0 + 1.0, lng=88.0),
        ]
    )
    result = validate_trip(TripItinerary(days=[day]))
    assert result.passed is False
    assert any("geo coherence" in e for e in result.errors)
    assert GEO_COHERENCE_MAX_STDDEV_KM == 15.0


def test_dropped_stops_warning_does_not_fail():
    day = _good_day(
        dropped_stops=[
            DroppedStop(
                place_id=uuid4(),
                name="Dropped",
                reason="exceeded_max_daily_travel",
            )
        ]
    )
    result = validate_trip(TripItinerary(days=[day]))
    assert result.passed is True
    assert result.errors == []
    assert _WARNING in result.warnings
