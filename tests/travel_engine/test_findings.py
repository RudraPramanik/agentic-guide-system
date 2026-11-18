"""Row 4.6 finding registry and per-code valid/invalid fixtures."""

from __future__ import annotations

from uuid import UUID, uuid4

from src.travel_engine.findings import FINDING_CODES, collect_findings, make_finding
from src.travel_engine.place_selector import PlaceCandidate
from src.travel_engine.schedule_builder import ScheduledStop
from src.travel_engine.travel_rules import BASE_SENTINEL_ID, MAX_DAILY_TRAVEL_MIN
from src.travel_engine.trip_validator import DayPlan, TripItinerary, validate_trip

_CODES = {
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
}


def _stop(
    name: str,
    *,
    place_id: UUID | None = None,
    start: str = "09:00",
    score: float = 1.0,
    lat: float = 27.0,
    lng: float = 88.0,
    category: str = "attraction",
    visit: int = 30,
    status: str = "verified",
    opening_open: str | None = "08:00",
    opening_close: str | None = "18:00",
    evidence: int = 1,
    tags: list[str] | None = None,
) -> ScheduledStop:
    return ScheduledStop(
        place=PlaceCandidate(
            id=place_id or uuid4(),
            name=name,
            category=category,
            enriched_tags=list(tags or []),
            lat=lat,
            lng=lng,
            evidence_count=evidence,
            opening_hours_status=status,  # type: ignore[arg-type]
            opening_open=opening_open,
            opening_close=opening_close,
        ),
        score=score,
        visit_duration_min=visit,
        suggested_start_time=start,
    )


def _itin(stops: list[ScheduledStop], travel: int = 10) -> TripItinerary:
    return TripItinerary(
        days=[DayPlan(stops=stops, total_travel_min=travel)]
    )


def _codes(itinerary: TripItinerary, **kwargs: object) -> set[str]:
    return {item.code for item in collect_findings(itinerary, **kwargs)}  # type: ignore[arg-type]


def test_registry_is_the_sixteen_codes() -> None:
    assert len(FINDING_CODES) == 16
    assert set(FINDING_CODES) == _CODES
    conflict = make_finding(
        "OPENING_HOURS_CONFLICT",
        day=0,
        stop_ids=[],
        message="conflict",
    )
    assert conflict.blocks_publish is True
    assert conflict.repairable is True
    assert conflict.suggested_action == "reoptimize_routes"
    unknown = make_finding(
        "OPENING_HOURS_UNKNOWN", day=0, stop_ids=[], message="unknown"
    )
    assert unknown.severity.value == "info"
    assert unknown.blocks_publish is False
    assert unknown.repairable is False
    assert unknown.suggested_action is None


def test_duplicate_stop() -> None:
    shared = uuid4()
    bad = _itin([_stop("A", place_id=shared), _stop("B", place_id=shared, start="10:00")])
    good = _itin([_stop("A"), _stop("B", start="10:00")])
    assert "DUPLICATE_STOP" in _codes(bad)
    assert "DUPLICATE_STOP" not in _codes(good)
    duplicate = next(item for item in collect_findings(bad) if item.code == "DUPLICATE_STOP")
    assert duplicate.blocks_publish is True


def test_invalid_coordinates() -> None:
    bad = _itin([_stop("A", lat=120.0)])
    good = _itin([_stop("A", lat=27.0)])
    assert "INVALID_COORDINATES" in _codes(bad)
    assert "INVALID_COORDINATES" not in _codes(good)


def test_missing_place_id() -> None:
    bad = _itin([_stop("Base", place_id=BASE_SENTINEL_ID)])
    good = _itin([_stop("Real")])
    assert "MISSING_PLACE_ID" in _codes(bad)
    assert "MISSING_PLACE_ID" not in _codes(good)


def test_out_of_search_area_requires_a_radius() -> None:
    far = _itin([_stop("Far", lat=27.0, lng=88.0)])
    assert "OUT_OF_SEARCH_AREA" not in _codes(far)
    assert "OUT_OF_SEARCH_AREA" in _codes(
        far, search_center=(0.0, 0.0), search_radius_km=1.0
    )
    assert "OUT_OF_SEARCH_AREA" not in _codes(
        far, search_center=(27.0, 88.0), search_radius_km=5.0
    )


def test_excessive_travel_keeps_v6_string_error() -> None:
    bad = _itin([_stop("A")], travel=MAX_DAILY_TRAVEL_MIN + 1)
    result = validate_trip(bad)
    assert result.passed is False
    assert any("exceeds daily travel cap" in error for error in result.errors)
    findings = collect_findings(bad)
    travel = next(item for item in findings if item.code == "EXCESSIVE_TRAVEL_TIME")
    assert travel.blocks_publish is False
    good = _itin([_stop("A")], travel=10)
    assert "EXCESSIVE_TRAVEL_TIME" not in _codes(good)


def test_overloaded_day() -> None:
    stops = [_stop(f"S{i}", start=f"{9 + i:02d}:00") for i in range(7)]
    bad = _itin(stops)
    good = _itin([_stop("Only")])
    assert "OVERLOADED_DAY" in _codes(bad)
    assert "OVERLOADED_DAY" not in _codes(good)


def test_malformed_hours_are_unknown_not_a_conflict() -> None:
    malformed = _itin(
        [
            _stop(
                "A",
                status="malformed",
                opening_open=None,
                opening_close=None,
            )
        ]
    )
    codes = _codes(malformed)
    assert "OPENING_HOURS_CONFLICT" not in codes
    assert "OPENING_HOURS_UNKNOWN" in codes


def test_opening_hours_conflict_and_unknown() -> None:
    conflict = _itin(
        [_stop("A", opening_open="08:00", opening_close="08:15", start="09:00")]
    )
    unknown = _itin(
        [_stop("A", status="unknown", opening_open=None, opening_close=None)]
    )
    verified = _itin([_stop("A", status="verified")])
    assert "OPENING_HOURS_CONFLICT" in _codes(conflict)
    assert "OPENING_HOURS_UNKNOWN" not in _codes(conflict)
    assert "OPENING_HOURS_UNKNOWN" in _codes(unknown)
    assert "OPENING_HOURS_CONFLICT" not in _codes(unknown)
    assert "OPENING_HOURS_CONFLICT" not in _codes(verified)
    assert "OPENING_HOURS_UNKNOWN" not in _codes(verified)


def test_missing_route_geometry_only_when_promised() -> None:
    day = _itin([_stop("A")])
    assert "MISSING_ROUTE_GEOMETRY" not in _codes(day)
    assert "MISSING_ROUTE_GEOMETRY" in _codes(
        day, geometry_promised=[True], geometry_missing=[True]
    )
    assert "MISSING_ROUTE_GEOMETRY" not in _codes(
        day, geometry_promised=[False], geometry_missing=[True]
    )


def test_route_schedule_mismatch() -> None:
    stops = [_stop("A", start="09:00", visit=30), _stop("B", start="09:40", visit=30)]
    day = _itin(stops)
    assert "ROUTE_SCHEDULE_MISMATCH" in _codes(day, leg_durations_min=[[100]])
    assert "ROUTE_SCHEDULE_MISMATCH" not in _codes(day, leg_durations_min=[[5]])
    assert "ROUTE_SCHEDULE_MISMATCH" not in _codes(day)


def test_non_chronological_schedule() -> None:
    bad = _itin([_stop("A", start="10:00"), _stop("B", start="09:00")])
    good = _itin([_stop("A", start="09:00"), _stop("B", start="10:00")])
    assert "NON_CHRONOLOGICAL_SCHEDULE" in _codes(bad)
    assert "NON_CHRONOLOGICAL_SCHEDULE" not in _codes(good)


def test_unrealistic_visit_sequence() -> None:
    bad = _itin(
        [_stop("A", start="09:00", visit=60), _stop("B", start="09:30", visit=30)]
    )
    good = _itin(
        [_stop("A", start="09:00", visit=30), _stop("B", start="10:00", visit=30)]
    )
    assert "UNREALISTIC_VISIT_SEQUENCE" in _codes(bad)
    assert "NON_CHRONOLOGICAL_SCHEDULE" not in _codes(bad)
    assert "UNREALISTIC_VISIT_SEQUENCE" not in _codes(good)


def test_insufficient_evidence() -> None:
    bad = _itin([_stop("A", evidence=0)])
    good = _itin([_stop("A", evidence=1)])
    assert "INSUFFICIENT_EVIDENCE" in _codes(bad)
    assert "INSUFFICIENT_EVIDENCE" not in _codes(good)


def test_morning_only_violation() -> None:
    bad = _itin([_stop("View", category="viewpoint", start="11:00", visit=20)])
    good = _itin([_stop("View", category="viewpoint", start="09:00", visit=20)])
    assert "MORNING_ONLY_VIOLATION" in _codes(bad)
    assert "MORNING_ONLY_VIOLATION" not in _codes(good)


def test_no_anchor_attraction() -> None:
    bad = _itin([_stop("Weak", score=0.1, tags=[])])
    good = _itin([_stop("Strong", score=1.0)])
    assert "NO_ANCHOR_ATTRACTION" in _codes(bad)
    assert "NO_ANCHOR_ATTRACTION" not in _codes(good)


def test_geo_incoherent_day() -> None:
    bad = _itin(
        [
            _stop("A", lat=27.0, lng=88.0),
            _stop("B", lat=28.0, lng=88.0, start="10:00"),
        ]
    )
    good = _itin(
        [
            _stop("A", lat=27.0, lng=88.0),
            _stop("B", lat=27.001, lng=88.001, start="10:00"),
        ]
    )
    assert "GEO_INCOHERENT_DAY" in _codes(bad)
    assert "GEO_INCOHERENT_DAY" not in _codes(good)


def test_findings_do_not_rewrite_a_passing_string_result() -> None:
    good = _itin([_stop("A", evidence=0)])
    result = validate_trip(good)
    assert result.passed is True
    assert result.errors == []
    assert "INSUFFICIENT_EVIDENCE" in _codes(good)
