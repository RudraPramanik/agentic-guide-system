"""Unit tests for travel_engine.place_selector (step 4.3 + v8.3 4.2)."""

from __future__ import annotations

from uuid import uuid4

from src.travel_engine.place_selector import (
    PlaceCandidate,
    TripPreferences,
    explain_selection,
    rank_candidates,
    score_place,
    select_places,
)
from src.travel_engine.travel_rules import (
    SCORE_KEY_DIVERSITY,
    SCORE_KEY_DUP_PENALTY,
    SCORE_KEY_EVIDENCE,
    SCORE_KEY_GEO_FIT,
    SCORE_KEY_REASONING_PRIORITY,
    SCORE_W_PRIORITY_HIGH,
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


def test_legacy_candidate_dict_still_validates() -> None:
    place_id = uuid4()
    place = PlaceCandidate.model_validate(
        {
            "id": str(place_id),
            "name": "Legacy",
            "category": "park",
            "enriched_tags": ["nature"],
            "lat": 27.0,
            "lng": 88.0,
        }
    )
    assert place.id == place_id
    assert place.user_selected is False
    assert place.aliases == []
    assert place.evidence_count == 0


def test_v2_off_matches_legacy_totals() -> None:
    prefs = TripPreferences(interests=["photography", "viewpoint"])
    place = _cand("Tiger Hill", "viewpoint", ["photography", "viewpoint"])
    legacy_total, legacy_bd = score_place(place, prefs.interests)
    off_total, off_bd = score_place(place, prefs.interests, v2_enabled=False)
    assert off_total == legacy_total
    assert off_bd == legacy_bd
    assert SCORE_KEY_DIVERSITY not in off_bd


def test_v2_on_breakdown_includes_configured_keys() -> None:
    prefs = TripPreferences(interests=["photography"])
    place = _cand("A", "viewpoint", ["photography"], lat=27.0, lng=88.0)
    total, breakdown = score_place(
        place,
        prefs.interests,
        v2_enabled=True,
        base_lat=27.0,
        base_lng=88.0,
        category_freq={"viewpoint": 1},
    )
    assert total > 1.4
    assert SCORE_KEY_DIVERSITY in breakdown
    assert SCORE_KEY_GEO_FIT in breakdown
    assert SCORE_KEY_EVIDENCE in breakdown
    assert SCORE_KEY_DUP_PENALTY in breakdown
    assert breakdown[SCORE_KEY_EVIDENCE] == 0.0


def test_v2_missing_evidence_scores_zero_for_term() -> None:
    place = _cand("Bare", "park", ["nature"])
    _, breakdown = score_place(
        place, ["nature"], v2_enabled=True, category_freq={"park": 1}
    )
    assert breakdown[SCORE_KEY_EVIDENCE] == 0.0


def test_explain_selection_includes_v2_term() -> None:
    place = _cand("Tiger Hill", "viewpoint", ["photography"])
    _, breakdown = score_place(
        place,
        ["photography"],
        v2_enabled=True,
        base_lat=27.0,
        base_lng=88.0,
        category_freq={"viewpoint": 1},
    )
    text = explain_selection(place, breakdown)
    assert "Tiger Hill" in text
    assert SCORE_KEY_DIVERSITY in text


def test_rank_candidates_v2_collapses_monastery_variants() -> None:
    prefs = TripPreferences(interests=["monastery"])
    a = _cand("Ghoom Monastery", "monastery", ["monastery"], lat=27.33, lng=88.13)
    b = _cand("ghoom monastery", "monastery", ["monastery"], lat=27.3301, lng=88.1301)
    ranked = rank_candidates([a, b], prefs, v2_enabled=True)
    assert len(ranked) == 1


def test_rank_candidates_v2_off_skips_normalizer() -> None:
    prefs = TripPreferences(interests=["monastery"])
    a = _cand("Ghoom Monastery", "monastery", ["monastery"], lat=27.33, lng=88.13)
    b = _cand("ghoom monastery", "monastery", ["monastery"], lat=27.3301, lng=88.1301)
    # AVOID_SAME_DAY still drops one monastery, but both enter scoring first;
    # with v2 off, no name-collapse before select — still one kept by pair rule.
    ranked = rank_candidates([a, b], prefs, v2_enabled=False)
    assert len(ranked) == 1
    # Flag-off path must not inject V2 breakdown keys
    assert SCORE_KEY_DIVERSITY not in ranked[0].score_breakdown


def test_empty_priority_map_matches_today() -> None:
    prefs = TripPreferences(interests=["photography", "offbeat"])
    multi = _cand("A", "viewpoint", ["photography", "offbeat"])
    single = _cand("B", "museum", ["photography"])
    base = select_places([multi, single], prefs)
    empty = select_places([multi, single], prefs, priorities={})
    none_map = select_places([multi, single], prefs, priorities=None)
    assert [s.score for s in empty] == [s.score for s in base]
    assert [s.score_breakdown for s in empty] == [s.score_breakdown for s in base]
    assert [s.score for s in none_map] == [s.score for s in base]
    assert SCORE_KEY_REASONING_PRIORITY not in empty[0].score_breakdown


def test_high_priority_cannot_outrank_interest_match() -> None:
    prefs = TripPreferences(interests=["photography"])
    matched = _cand("Match", "viewpoint", ["photography"])
    boosted = _cand("Boost", "park", [])
    scored = select_places(
        [matched, boosted],
        prefs,
        priorities={boosted.id: "high"},
    )
    assert scored[0].place.name == "Match"
    assert scored[0].score > scored[1].score
    assert scored[1].score_breakdown[SCORE_KEY_REASONING_PRIORITY] == SCORE_W_PRIORITY_HIGH


def test_unknown_priority_id_ignored() -> None:
    prefs = TripPreferences(interests=["photography"])
    place = _cand("A", "viewpoint", ["photography"])
    scored = select_places(
        [place],
        prefs,
        priorities={uuid4(): "high"},
    )
    assert SCORE_KEY_REASONING_PRIORITY not in scored[0].score_breakdown
    assert scored[0].score == 1.4


def test_low_priority_adds_nothing() -> None:
    prefs = TripPreferences(interests=["photography"])
    place = _cand("A", "viewpoint", ["photography"])
    scored = select_places([place], prefs, priorities={place.id: "low"})
    assert scored[0].score_breakdown[SCORE_KEY_REASONING_PRIORITY] == 0.0
    assert scored[0].score == 1.4


def test_omitted_hours_default_unknown_and_scoring_ignores_them() -> None:
    bare = PlaceCandidate(
        id=uuid4(),
        name="Bare",
        category="park",
        lat=27.0,
        lng=88.0,
    )
    assert bare.opening_hours_status == "unknown"
    assert bare.opening_open is None
    assert bare.opening_close is None
    prefs = TripPreferences(interests=["photography"])
    plain = _cand("A", "viewpoint", ["photography"])
    verified = _cand("B", "viewpoint", ["photography"])
    verified.opening_hours_status = "verified"
    verified.opening_open = "08:00"
    verified.opening_close = "12:00"
    assert score_place(plain, prefs.interests)[0] == score_place(
        verified, prefs.interests
    )[0]
