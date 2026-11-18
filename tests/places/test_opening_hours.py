"""Opening-hours grammar and flag-gated mapping."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from src.places.opening_hours import apply_hours, parse_opening_hours
from src.planner.tools._helpers import place_to_candidate
from src.travel_engine.place_selector import PlaceCandidate, score_place


def test_absent_and_whitespace_are_unknown() -> None:
    for raw in (None, "  "):
        parsed = parse_opening_hours(raw)
        assert parsed.status == "unknown"
        assert parsed.raw is None
        assert parsed.opening_open is None
        assert parsed.opening_close is None


def test_all_week_and_always_open_are_verified() -> None:
    window = parse_opening_hours("Mo-Su 09:00-17:00")
    assert window.status == "verified"
    assert window.raw == "Mo-Su 09:00-17:00"
    assert window.opening_open == "09:00"
    assert window.opening_close == "17:00"
    always = parse_opening_hours("24/7")
    assert always.status == "verified"
    assert always.opening_open == "00:00"
    assert always.opening_close == "24:00"


def test_closed_is_an_empty_verified_window() -> None:
    parsed = parse_opening_hours("off")
    assert parsed.status == "verified"
    assert parsed.opening_open == "00:00"
    assert parsed.opening_close == "00:00"


def test_weekday_only_stays_unknown() -> None:
    parsed = parse_opening_hours("Mo-Fr 09:00-17:00")
    assert parsed.status == "unknown"
    assert parsed.raw == "Mo-Fr 09:00-17:00"
    assert parsed.opening_open is None
    assert parsed.opening_close is None


def test_unrecognized_text_is_malformed() -> None:
    parsed = parse_opening_hours("every morning")
    assert parsed.status == "malformed"
    assert parsed.raw == "every morning"
    assert parsed.opening_open is None
    assert parsed.opening_close is None


def test_flag_off_ignores_a_present_tag(monkeypatch) -> None:
    settings = SimpleNamespace(READINESS_V2_ENABLED=False)
    monkeypatch.setattr("src.planner.tools._helpers.get_settings", lambda: settings)
    place = SimpleNamespace(
        id=uuid4(),
        name="Hill",
        category="viewpoint",
        enriched_tags=[],
        tags={"opening_hours": "Mo-Su 09:00-17:00"},
        osm_id="1",
        location=SimpleNamespace(y=27.0, x=88.0),
    )
    monkeypatch.setattr(
        "src.planner.tools._helpers.to_shape",
        lambda _location: place.location,
    )
    candidate = place_to_candidate(place)  # type: ignore[arg-type]
    assert candidate.opening_hours_status == "unknown"
    assert candidate.opening_open is None
    assert candidate.opening_close is None
    assert candidate.opening_hours_raw is None


def test_flag_on_copies_a_verified_window(monkeypatch) -> None:
    settings = SimpleNamespace(READINESS_V2_ENABLED=True)
    monkeypatch.setattr("src.planner.tools._helpers.get_settings", lambda: settings)
    place = SimpleNamespace(
        id=uuid4(),
        name="Hill",
        category="viewpoint",
        enriched_tags=[],
        tags={"opening_hours": "Mo-Su 09:00-17:00"},
        osm_id="1",
        location=SimpleNamespace(y=27.0, x=88.0),
    )
    monkeypatch.setattr(
        "src.planner.tools._helpers.to_shape",
        lambda _location: place.location,
    )
    candidate = place_to_candidate(place)  # type: ignore[arg-type]
    assert candidate.opening_hours_status == "verified"
    assert candidate.opening_open == "09:00"
    assert candidate.opening_close == "17:00"


def test_hours_do_not_change_the_score() -> None:
    left = PlaceCandidate(
        id=uuid4(),
        name="A",
        category="attraction",
        enriched_tags=["photography"],
        lat=27.0,
        lng=88.0,
        opening_hours_status="unknown",
    )
    right = left.model_copy(
        update={
            "opening_hours_status": "verified",
            "opening_hours_raw": "Mo-Su 09:00-17:00",
            "opening_open": "09:00",
            "opening_close": "17:00",
        }
    )
    assert score_place(left, ["photography"])[0] == score_place(right, ["photography"])[0]


def test_legacy_candidate_omits_raw_hours() -> None:
    candidate = PlaceCandidate(
        id=uuid4(),
        name="A",
        category="attraction",
        enriched_tags=[],
        lat=1.0,
        lng=2.0,
    )
    assert candidate.opening_hours_raw is None


def test_engine_does_not_parse_hours_or_read_the_flag() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "travel_engine"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "parse_opening_hours" not in text
        assert "READINESS_V2_ENABLED" not in text


def test_apply_hours_disabled_keeps_defaults() -> None:
    candidate = PlaceCandidate(
        id=uuid4(),
        name="A",
        category="attraction",
        lat=1.0,
        lng=2.0,
    )
    same = apply_hours(candidate, {"opening_hours": "24/7"}, False)
    assert same.opening_hours_status == "unknown"
    assert same.opening_hours_raw is None
