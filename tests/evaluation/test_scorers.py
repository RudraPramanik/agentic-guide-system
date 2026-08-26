"""Unit tests for golden-eval scorers."""

from __future__ import annotations

from src.evaluation.scorers import score_case


def test_score_case_deterministic() -> None:
    result = {
        "days": 3,
        "validation_result": {"ok": True},
        "readiness_score": 0.8,
        "used_geo_fallback": False,
        "tool_loop_count": 4,
        "itinerary": {
            "days": [
                {
                    "day": 1,
                    "stops": [
                        {"name": "Tiger Hill", "place_id": "a"},
                        {"name": "Batasia", "place_id": "b"},
                        {"name": "Zoo", "place_id": "c"},
                    ],
                }
            ]
        },
    }
    case = {
        "id": "dar-001",
        "must_include_places": ["Tiger Hill"],
        "assertions": {
            "validation_passed": True,
            "max_days": 3,
            "min_places_per_day": 3,
            "readiness_score_min": 0.6,
            "no_geo_fallback": True,
            "max_tool_calls": 10,
        },
    }
    a = score_case(result, case)
    b = score_case(result, case)
    assert a == b
    assert a.passed is True


def test_score_case_missing_place_fails() -> None:
    result = {
        "validation_result": {"ok": True},
        "itinerary": {"days": [{"day": 1, "stops": [{"name": "Zoo"}]}]},
    }
    case = {
        "must_include_places": ["Tiger Hill"],
        "assertions": {"validation_passed": True},
    }
    v = score_case(result, case)
    assert v.passed is False
    assert any(r.startswith("missing_place:") for r in v.reasons)
