"""Golden case schema v2 loader. No LLM, network, or database I/O."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CASE_TYPES = frozenset(
    {
        "landmark_vs_city",
        "ambiguous_name",
        "map_pin_radius",
        "neighborhood_or_address",
        "sparse_data",
        "multi_day",
        "duplicate_prone",
        "routing_failure",
        "llm_unavailable",
        "over_travel_budget",
        "unknown_opening_hours",
        "guide_suggestion",
        "itinerary_preference",
    }
)

_REQUIRED_KEYS = (
    "schema_version",
    "id",
    "destination",
    "raw_input",
    "case_type",
    "labels",
    "quarantined",
    "assertions",
)

_ASSERTION_KINDS = {
    "validation_passed": "bool",
    "max_days": "int",
    "min_places_per_day": "int",
    "readiness_score_min": "number",
    "no_geo_fallback": "bool",
    "max_tool_calls": "int",
}


class GoldenCaseError(Exception):
    """A golden file failed schema v2. Message is `{filename}: {code}`."""

    def __init__(self, code: str, filename: str) -> None:
        self.code = code
        self.filename = filename
        super().__init__(f"{filename}: {code}")


def load_golden_cases(folder: Path) -> list[dict[str, Any]]:
    """Load `*.json` in file-name order. The first bad file aborts the load."""
    cases: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        cases.append(_load_one(path))
    return cases


def _load_one(path: Path) -> dict[str, Any]:
    filename = path.name
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise GoldenCaseError("invalid_json", filename) from exc
    if not isinstance(data, dict):
        raise GoldenCaseError("not_an_object", filename)
    _validate(data, filename)
    return data


def _fail(code: str, filename: str) -> None:
    raise GoldenCaseError(code, filename)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and value != ""


def _validate(data: dict[str, Any], filename: str) -> None:
    for key in _REQUIRED_KEYS:
        if key not in data:
            _fail("missing_field", filename)

    if not _non_empty_str(data["id"]):
        _fail("invalid_field", filename)
    if not _non_empty_str(data["destination"]):
        _fail("invalid_field", filename)
    if not _non_empty_str(data["raw_input"]):
        _fail("invalid_field", filename)

    version = data["schema_version"]
    if not _is_int(version) or version != 2:
        _fail("invalid_schema_version", filename)

    if data["case_type"] not in CASE_TYPES:
        _fail("invalid_case_type", filename)

    labels = data["labels"]
    if not isinstance(labels, list):
        _fail("invalid_labels", filename)
    seen: set[str] = set()
    for label in labels:
        if not _non_empty_str(label) or label in seen:
            _fail("invalid_labels", filename)
        seen.add(label)

    quarantined = data["quarantined"]
    if not isinstance(quarantined, bool):
        _fail("invalid_quarantine", filename)
    if quarantined is False:
        if "quarantine_owner" in data:
            _fail("invalid_quarantine", filename)
    else:
        owner = data.get("quarantine_owner")
        if not _non_empty_str(owner):
            _fail("missing_quarantine_owner", filename)

    if "destination_id" in data and not _non_empty_str(data["destination_id"]):
        _fail("invalid_field", filename)

    if "must_include_places" in data:
        places = data["must_include_places"]
        if not isinstance(places, list) or any(not _non_empty_str(place) for place in places):
            _fail("invalid_field", filename)

    assertions = data["assertions"]
    if not isinstance(assertions, dict) or not assertions:
        _fail("empty_assertions", filename)

    for key, value in assertions.items():
        kind = _ASSERTION_KINDS.get(key)
        if kind is None:
            _fail("unknown_assertion", filename)
        if kind == "bool":
            ok = isinstance(value, bool)
        elif kind == "int":
            ok = _is_int(value)
        else:
            ok = _is_number(value)
        if not ok:
            _fail("invalid_assertion_value", filename)
