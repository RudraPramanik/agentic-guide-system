"""Schema v2 golden loader. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluation.golden import GoldenCaseError, load_golden_cases

_DARJEELING = Path(__file__).resolve().parents[2] / "evals" / "golden" / "darjeeling"
_SIX_KEYS = {
    "validation_passed",
    "max_days",
    "min_places_per_day",
    "readiness_score_min",
    "no_geo_fallback",
    "max_tool_calls",
}


def _case(**overrides: object) -> dict:
    data: dict = {
        "schema_version": 2,
        "id": "dar-001",
        "destination": "Darjeeling",
        "raw_input": "3 days photography sunrise Tiger Hill",
        "case_type": "itinerary_preference",
        "labels": ["darjeeling"],
        "quarantined": False,
        "assertions": {"validation_passed": True},
        "destination_id": "458854b1-4d2a-4d02-8901-e26ed59c0c8b",
    }
    data.update(overrides)
    return data


def _write(folder: Path, name: str, body: dict) -> None:
    (folder / name).write_text(json.dumps(body), encoding="utf-8")


def _expect(folder: Path, name: str, code: str) -> None:
    with pytest.raises(GoldenCaseError) as caught:
        load_golden_cases(folder)
    assert caught.value.code == code
    assert caught.value.filename == name
    assert str(caught.value) == f"{name}: {code}"


def test_schema_v2_case_loads_unchanged(tmp_path: Path) -> None:
    body = _case()
    _write(tmp_path, "dar-001.json", body)
    loaded = load_golden_cases(tmp_path)
    assert loaded == [body]


def test_missing_schema_version_names_the_file(tmp_path: Path) -> None:
    body = _case()
    del body["schema_version"]
    _write(tmp_path, "dar-001.json", body)
    _expect(tmp_path, "dar-001.json", "missing_field")


def test_unknown_case_type_names_the_file(tmp_path: Path) -> None:
    _write(tmp_path, "dar-001.json", _case(case_type="city"))
    _expect(tmp_path, "dar-001.json", "invalid_case_type")


def test_unknown_assertion_key_names_the_file(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "dar-001.json",
        _case(assertions={"narrative_contains": "sunrise"}),
    )
    _expect(tmp_path, "dar-001.json", "unknown_assertion")


def test_string_max_days_names_the_file(tmp_path: Path) -> None:
    _write(tmp_path, "dar-001.json", _case(assertions={"max_days": "3"}))
    _expect(tmp_path, "dar-001.json", "invalid_assertion_value")


def test_quarantined_without_owner_names_the_file(tmp_path: Path) -> None:
    _write(tmp_path, "dar-001.json", _case(quarantined=True))
    _expect(tmp_path, "dar-001.json", "missing_quarantine_owner")


def test_owner_on_non_quarantined_case_names_the_file(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "dar-001.json",
        _case(quarantined=False, quarantine_owner="reviewer"),
    )
    _expect(tmp_path, "dar-001.json", "invalid_quarantine")


def test_quarantined_case_stays_loaded(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.json",
        _case(id="a", quarantined=True, quarantine_owner="reviewer"),
    )
    loaded = load_golden_cases(tmp_path)
    assert len(loaded) == 1
    assert loaded[0]["quarantined"] is True
    assert loaded[0]["quarantine_owner"] == "reviewer"


def test_quarantined_and_normal_cases_both_return(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.json",
        _case(id="a", quarantined=True, quarantine_owner="reviewer"),
    )
    _write(tmp_path, "b.json", _case(id="b", quarantined=False))
    loaded = load_golden_cases(tmp_path)
    assert [case["id"] for case in loaded] == ["a", "b"]
    assert [case["quarantined"] for case in loaded] == [True, False]


def test_all_six_assertion_keys_round_trip(tmp_path: Path) -> None:
    assertions = {
        "validation_passed": True,
        "max_days": 3,
        "min_places_per_day": 2,
        "readiness_score_min": 0.3,
        "no_geo_fallback": True,
        "max_tool_calls": 12,
    }
    _write(tmp_path, "dar-001.json", _case(assertions=assertions))
    loaded = load_golden_cases(tmp_path)
    assert set(loaded[0]["assertions"]) == _SIX_KEYS
    assert loaded[0]["assertions"] == assertions


def test_darjeeling_cases_keep_their_ids() -> None:
    loaded = load_golden_cases(_DARJEELING)
    expected = [f"dar-{index:03d}" for index in range(1, 13)]
    assert [case["id"] for case in loaded] == expected
    assert {case["schema_version"] for case in loaded} == {2}
    assert {case["case_type"] for case in loaded} == {"itinerary_preference"}
