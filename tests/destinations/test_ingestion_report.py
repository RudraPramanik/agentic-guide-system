"""Ingestion report over checked-in samples."""

from __future__ import annotations

import json
from pathlib import Path

from src.destinations.ingestion_report import load_fixture_dir, report_destination

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "evals" / "fixtures" / "ingestion"


def test_darjeeling_duplicate_rate_and_failure() -> None:
    payload = json.loads((FIXTURES / "darjeeling.json").read_text(encoding="utf-8"))
    section = report_destination(payload)
    assert section["place_count"] == 2
    assert section["duplicate_rate"] == 0.5
    assert section["failure_count"] == 1
    assert section["failures"] == ["overpass_timeout"]


def test_manali_stale_timestamps_are_not_fresh() -> None:
    payload = json.loads((FIXTURES / "manali.json").read_text(encoding="utf-8"))
    section = report_destination(payload)
    assert section["freshness_share"] == 0.0


def test_three_fixtures_load() -> None:
    report = load_fixture_dir(FIXTURES)
    names = [item["destination"] for item in report["destinations"]]
    assert names == ["Darjeeling", "Manali", "Goa"]


def test_missing_fixture_names_the_destination(tmp_path: Path) -> None:
    (tmp_path / "darjeeling.json").write_text(
        json.dumps({"as_of": "2026-01-31", "destination": "Darjeeling", "places": [], "failures": []}),
        encoding="utf-8",
    )
    (tmp_path / "manali.json").write_text(
        json.dumps({"as_of": "2026-01-31", "places": [], "failures": []}),
        encoding="utf-8",
    )
    try:
        load_fixture_dir(tmp_path)
    except FileNotFoundError as exc:
        assert str(exc) == "goa"
    else:
        raise AssertionError("expected missing Goa fixture")
