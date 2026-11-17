"""Seeded regression gate: named diffs, quarantine exclusion, explicit baseline writes."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_evals import _tolerance_failures, finish_run, gate_pass_rate


def _report(cases: list[dict], metrics: dict | None = None) -> dict:
    return {
        "case_set_hash": "abc",
        "pass_rate": gate_pass_rate(cases),
        "cases": cases,
        "metrics": metrics or {},
    }


def _finish(report: dict, baseline: Path, *, update: bool = False, tolerances: dict | None = None):
    return finish_run(
        report,
        baseline_path=baseline,
        tolerances=tolerances or {},
        update_baseline=update,
        allow_new_fails=False,
    )


def test_seeded_regression_names_case_and_exits_nonzero(tmp_path: Path) -> None:
    baseline = tmp_path / "darjeeling.json"
    baseline.write_text(
        json.dumps(
            _report(
                [{"id": "seed-pass", "passed": True, "quarantined": False, "reasons": []}]
            )
        ),
        encoding="utf-8",
    )
    code, lines = _finish(
        _report(
            [
                {
                    "id": "seed-pass",
                    "passed": False,
                    "quarantined": False,
                    "reasons": ["seed"],
                }
            ]
        ),
        baseline,
    )
    text = "\n".join(lines)
    assert code != 0
    assert "REGRESSION" in text
    assert "seed-pass" in text


def test_quarantined_only_fail_exits_zero(tmp_path: Path) -> None:
    baseline = tmp_path / "darjeeling.json"
    baseline.write_text(
        json.dumps(
            _report([{"id": "q1", "passed": True, "quarantined": True, "reasons": []}])
        ),
        encoding="utf-8",
    )
    cases = [{"id": "q1", "passed": False, "quarantined": True, "reasons": ["flake"]}]
    assert gate_pass_rate(cases) == 1.0
    code, _lines = _finish(_report(cases), baseline)
    assert code == 0


def test_normal_run_does_not_change_baseline_bytes(tmp_path: Path) -> None:
    baseline = tmp_path / "darjeeling.json"
    original = json.dumps(
        _report(
            [{"id": "seed-pass", "passed": True, "quarantined": False, "reasons": []}]
        )
    )
    baseline.write_text(original, encoding="utf-8")
    before = baseline.read_bytes()
    code, _lines = _finish(
        _report(
            [{"id": "seed-pass", "passed": True, "quarantined": False, "reasons": []}]
        ),
        baseline,
    )
    assert code == 0
    assert baseline.read_bytes() == before


def test_update_baseline_writes_the_report(tmp_path: Path) -> None:
    baseline = tmp_path / "darjeeling.json"
    report = _report(
        [{"id": "seed-pass", "passed": True, "quarantined": False, "reasons": []}]
    )
    code, lines = _finish(report, baseline, update=True)
    assert code == 0
    assert any("updated baseline" in line for line in lines)
    assert json.loads(baseline.read_text(encoding="utf-8"))["cases"][0]["id"] == "seed-pass"


def test_unlisted_metric_does_not_fail() -> None:
    assert _tolerance_failures({"duplicate_stop_count": 9, "coherence_km": 40}, {}) == []


def test_measured_band_prints_tolerance() -> None:
    lines = _tolerance_failures(
        {"duplicate_stop_count": 2},
        {
            "duplicate_stop_count": {
                "baseline": 0,
                "tolerance": 0,
                "higher_is_worse": True,
            }
        },
    )
    assert lines
    assert lines[0].startswith("TOLERANCE duplicate_stop_count")
