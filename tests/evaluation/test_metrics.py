"""Hand-computed expectations for the deterministic metrics."""

from __future__ import annotations

import json
from pathlib import Path

from src.evaluation.metrics import (
    duplicate_stop_count,
    geographic_coherence_km,
    location_type_accuracy,
    map_itinerary_match,
    persistence_match,
    preference_match,
    retrieval_recall_at_k,
    schedule_feasibility,
)
from src.evaluation.scorers import score_case

_ROOT = Path(__file__).resolve().parents[2]


def test_location_type_accuracy_two_of_three() -> None:
    labeled = ["city", "landmark", "poi"]
    predicted = ["city", "landmark", "city"]
    assert location_type_accuracy(predicted, labeled) == 2 / 3


def test_location_type_accuracy_empty_labels() -> None:
    assert location_type_accuracy([], []) == 1.0


def test_recall_one_of_two_in_top_ten() -> None:
    retrieved = ["a", "c", "d", "e", "f", "g", "h", "i", "j", "k"]
    assert retrieval_recall_at_k(retrieved, ["a", "b"], 10) == 0.5


def test_recall_repeated_hit_counts_once() -> None:
    retrieved = ["a", "a"] + ["x"] * 8
    assert retrieval_recall_at_k(retrieved, ["a"], 10) == 1.0


def test_duplicate_counts() -> None:
    assert duplicate_stop_count(["a", "a", "b"]) == 1
    assert duplicate_stop_count(["a", "a", "a"]) == 2
    assert duplicate_stop_count(["a", "b", "c"]) == 0


def test_coherence_none_and_zero() -> None:
    assert geographic_coherence_km([(1.0, 2.0)]) is None
    assert geographic_coherence_km([(1.0, 2.0), (1.0, 2.0)]) == 0.0


def test_coherence_farther_point_scores_higher() -> None:
    original = [(0.0, 0.0), (0.0, 0.02)]
    base = geographic_coherence_km(original)
    assert base is not None
    farther = geographic_coherence_km(original + [(1.0, 0.01)])
    assert farther is not None
    assert farther > base


def test_feasibility_half_and_empty() -> None:
    days = [(30, 10), (30, 50)]
    assert schedule_feasibility(days, active_cap=40, travel_cap=20) == 0.5
    assert schedule_feasibility([], active_cap=40, travel_cap=20) == 1.0


def test_preference_one_of_two() -> None:
    places = [("tea", []), ("museum", [])]
    assert preference_match(places, ["tea"]) == 0.5
    assert preference_match([], ["tea"]) == 1.0


def test_persistence_order() -> None:
    generated = [["p1", "p2"], ["p3"]]
    assert persistence_match(generated, [["p1", "p2"], ["p3"]]) is True
    assert persistence_match(generated, [["p2", "p1"], ["p3"]]) is False


def test_map_feature_order() -> None:
    assert map_itinerary_match(["p1", "p2"], ["p1", "p2"]) is True
    assert map_itinerary_match(["p1", "p2", "extra"], ["p1", "p2"]) is False


def test_metrics_are_deterministic() -> None:
    coords = [(27.0, 88.0), (27.01, 88.01)]
    assert geographic_coherence_km(coords) == geographic_coherence_km(coords)


def test_darjeeling_case_verdict_unchanged() -> None:
    path = _ROOT / "evals" / "golden" / "darjeeling" / "dar-001.json"
    case = json.loads(path.read_text(encoding="utf-8-sig"))
    result = {
        "days": 1,
        "validation_result": {"passed": True},
        "readiness_score": 0.5,
        "used_geo_fallback": False,
        "tool_loop_count": 1,
        "itinerary": {"days": [{"stops": [{"name": "Tiger Hill"}]}]},
    }
    verdict = score_case(result, case)
    assert verdict.passed is True
    assert verdict.reasons == []
