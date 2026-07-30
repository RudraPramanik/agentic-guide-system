"""Unit tests for travel_engine.place_selector (step 4.3)."""

from __future__ import annotations

from uuid import uuid4

from src.travel_engine.place_selector import (
    PlaceCandidate,
    TripPreferences,
    explain_selection,
    score_place,
    select_places,
)


def _cand(
    name: str,
    category: str,
    tags: list[str] | None = None,
    *,
    lat: float = 27.0,
    lng: float = 88.0,
) -> PlaceCandidate:
    return PlaceCandidate(
        id=uuid4(),
        name=name,
        category=category,
        enriched_tags=tags or [],
        lat=lat,
        lng=lng,
    )


def test_multi_interest_outranks_single() -> None:
    prefs = TripPreferences(interests=["photography", "offbeat"])
    multi = _cand("A", "viewpoint", ["photography", "offbeat"])
    single = _cand("B", "museum", ["photography"])
    scored = select_places([multi, single], prefs)
    assert scored[0].place.name == "A"
    assert scored[0].score > scored[1].score


def test_empty_enriched_tags_scores_zero_still_returned() -> None:
    prefs = TripPreferences(interests=["photography"])
    empty = _cand("C", "park", [])
    scored = select_places([empty], prefs)
    assert len(scored) == 1
    assert scored[0].score == 0.0


def test_empty_candidates_returns_empty() -> None:
    prefs = TripPreferences(interests=["photography"])
    assert select_places([], prefs) == []


def test_empty_interests_all_scores_zero() -> None:
    prefs = TripPreferences(interests=[])
    places = [
        _cand("A", "viewpoint", ["photography", "offbeat"]),
        _cand("B", "museum", ["photography"]),
    ]
    scored = select_places(places, prefs)
    assert len(scored) == 2
    assert all(s.score == 0.0 for s in scored)


def test_monastery_conflict_drops_lower_score() -> None:
    prefs = TripPreferences(interests=["monastery", "cultural"])
    high = _cand("HighMon", "monastery", ["monastery", "cultural"])
    low = _cand("LowMon", "monastery", ["monastery"])
    scored = select_places([high, low], prefs)
    names = [s.place.name for s in scored]
    assert "HighMon" in names
    assert "LowMon" not in names


def test_unknown_tags_do_not_keyerror() -> None:
    prefs = TripPreferences(interests=["photography", "not_a_real_interest"])
    place = _cand("X", "attraction", ["photography", "totally_unknown_tag"])
    total, breakdown = score_place(place, prefs.interests)
    assert total == 1.4
    assert "photography" in breakdown
    assert "totally_unknown_tag" not in breakdown
    scored = select_places([place], prefs)
    assert scored[0].score == 1.4


def test_explain_selection_includes_name_and_breakdown() -> None:
    place = _cand("Tiger Hill", "viewpoint", ["photography", "viewpoint"])
    _, breakdown = score_place(place, ["photography", "viewpoint"])
    text = explain_selection(place, breakdown)
    assert "Tiger Hill" in text
    assert "photography" in text
    assert "1.4" in text


def test_tie_break_stable_by_name() -> None:
    prefs = TripPreferences(interests=["photography"])
    b = _cand("Beta", "museum", ["photography"])
    a = _cand("Alpha", "park", ["photography"])
    scored = select_places([b, a], prefs)
    assert scored[0].score == scored[1].score
    assert scored[0].place.name == "Alpha"
    assert scored[1].place.name == "Beta"
