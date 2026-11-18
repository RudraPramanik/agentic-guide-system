"""Retrieval suite gate. Does not call the planner."""

from __future__ import annotations

import json
from pathlib import Path

from src.evaluation.retrieval_suite import METRIC_NAME, run_retrieval_suite
from src.evaluation.scorers import score_case

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "evals" / "golden" / "retrieval"
BASELINE = ROOT / "evals" / "baselines" / "retrieval.json"


def _darjeeling_verdict():
    result = {
        "days": 3,
        "validation_result": {"ok": True},
        "readiness_score": 0.8,
        "used_geo_fallback": False,
        "tool_loop_count": 4,
        "itinerary": {
            "days": [
                {
                    "stops": [
                        {"name": "Tiger Hill"},
                        {"name": "Batasia"},
                        {"name": "Zoo"},
                    ]
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
            "readiness_score_min": 0.6,
            "no_geo_fallback": True,
            "max_tool_calls": 10,
        },
    }
    return score_case(result, case)


def test_checked_in_suite_meets_the_floor() -> None:
    before = _darjeeling_verdict()
    code, messages = run_retrieval_suite(CASES, BASELINE)
    after = _darjeeling_verdict()
    assert code == 0
    assert any("0.8" in line for line in messages)
    assert before.passed is True
    assert after.passed == before.passed
    assert after.reasons == before.reasons


def test_case_under_floor_fails(tmp_path: Path) -> None:
    folder = tmp_path / "cases"
    folder.mkdir()
    (folder / "low.json").write_text(
        json.dumps(
            {
                "id": "low",
                "retrieved": ["a", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9"],
                "must_include": ["a", "b"],
            }
        ),
        encoding="utf-8",
    )
    code, messages = run_retrieval_suite(folder, tmp_path / "missing.json")
    assert code == 1
    assert any("0.5" in line for line in messages)


def test_mean_below_baseline_names_the_metric(tmp_path: Path) -> None:
    folder = tmp_path / "cases"
    folder.mkdir()
    (folder / "floor.json").write_text(
        (CASES / "ret-002-four-of-five.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    baseline = tmp_path / "retrieval.json"
    baseline.write_text(json.dumps({METRIC_NAME: 0.95}), encoding="utf-8")
    code, messages = run_retrieval_suite(folder, baseline)
    assert code == 1
    assert any(METRIC_NAME in line for line in messages)
