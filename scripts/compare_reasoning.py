"""Slice 7.4 reasoning ship-gate comparison (replay / fixtures only).

Usage:
  python scripts/compare_reasoning.py
  python scripts/compare_reasoning.py --destination darjeeling

Does not update baselines. Does not set REASONING_LAYER_ENABLED=true.
A missing treatment fixture is a named miss (no live provider call).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.golden import GoldenCaseError, load_golden_cases  # noqa: E402
from src.evaluation.scorers import score_case  # noqa: E402


def _load_cases(dest: str) -> list[dict[str, Any]]:
    folder = ROOT / "evals" / "golden" / dest
    if not folder.is_dir():
        raise SystemExit(f"missing golden folder: {folder}")
    try:
        cases = load_golden_cases(folder)
    except GoldenCaseError as exc:
        raise SystemExit(str(exc)) from exc
    return cases


def _load_fixture(case_id: str) -> dict[str, Any] | None:
    path = ROOT / "evals" / "fixtures" / f"{case_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _paired_human_reviews() -> list[dict[str, Any]]:
    folder = ROOT / "evals" / "human_review"
    pairs: list[dict[str, Any]] = []
    if not folder.is_dir():
        return pairs
    for path in sorted(folder.glob("*.json")):
        if path.name == "example.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("control") is not None and data.get("treatment") is not None:
            pairs.append({"path": path.name, **data})
    return pairs


def _s0_targets_unmeasured() -> list[str]:
    path = ROOT / "docs" / "v8.2" / "s0_targets.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    cells: list[str] = []
    for label in (
        "Generate p50 latency",
        "LLM calls per trip",
        "Tokens per trip",
        "Cost per trip",
    ):
        if "[SET IN S0]" in text and label.split()[0] in text:
            cells.append(label)
    # Explicit: these four are known unmeasured from S0.
    return [
        "Generate p50 latency",
        "LLM calls per trip",
        "Tokens per trip",
        "Cost per trip",
    ]


def _score_fixture(case: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    verdict = score_case(fixture, case)
    return {
        "passed": bool(verdict.passed),
        "reasons": list(verdict.reasons),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Slice 7 reasoning ship comparison")
    parser.add_argument("--destination", default="darjeeling")
    args = parser.parse_args()

    cases = _load_cases(args.destination)
    control_rows: list[dict[str, Any]] = []
    treatment_rows: list[dict[str, Any]] = []
    fixture_misses: list[str] = []

    both_scored: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for case in cases:
        if case.get("quarantined"):
            continue
        case_id = str(case["id"])
        fixture = _load_fixture(case_id)
        if fixture is None:
            fixture_misses.append(case_id)
            treatment_rows.append(
                {
                    "id": case_id,
                    "status": "fixture_miss",
                    "note": "no control fixture; provider not called",
                }
            )
            continue
        control = _score_fixture(case, fixture)
        control_rows.append({"id": case_id, "control": control})
        # Treatment needs reasoner fixtures. Absent → named miss (no live call).
        treatment_fixture_path = (
            ROOT / "evals" / "fixtures" / f"{case_id}.reasoning.json"
        )
        if not treatment_fixture_path.is_file():
            fixture_misses.append(f"{case_id}.reasoning")
            treatment_rows.append(
                {
                    "id": case_id,
                    "status": "fixture_miss",
                    "note": "missing treatment fixture; provider not called",
                }
            )
            continue
        treatment_fixture = json.loads(
            treatment_fixture_path.read_text(encoding="utf-8-sig")
        )
        treatment = _score_fixture(case, treatment_fixture)
        treatment_rows.append({"id": case_id, "treatment": treatment})
        both_scored.append((control, treatment))

    human_pairs = _paired_human_reviews()
    unmeasured = _s0_targets_unmeasured()
    human_clause_met = len(human_pairs) > 0
    deterministic_ok = all(t.get("passed", False) for _, t in both_scored)
    if not both_scored:
        deterministic_ok = False

    ship_clauses = {
        "deterministic_gates": deterministic_ok and len(fixture_misses) == 0,
        "human_margin": False,
        "human_pairs_present": human_clause_met,
        "p95_within_45s": False,  # unmeasured
        "tokens_cost_within_s0": False,  # unmeasured cells
        "failure_rate_no_worse": len(fixture_misses) == 0,
    }
    decision = "stay_off"
    if all(ship_clauses.values()):
        decision = "eligible_to_enable_later"

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "destination": args.destination,
        "case_count": len(cases),
        "control_rows": control_rows,
        "treatment_rows": treatment_rows,
        "fixture_misses": fixture_misses,
        "human_pairs": [p.get("path") for p in human_pairs],
        "human_clause_met": human_clause_met,
        "unmeasured_s0_cells": unmeasured,
        "pre_registered_margin": {
            "pass_rate_pp": 10,
            "scale_delta": 0.3,
            "ci_excludes_zero": True,
        },
        "ship_clauses": ship_clauses,
        "decision": decision,
        "baseline_updated": False,
        "provider_called": False,
    }

    runs = ROOT / "evals" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = runs / f"{stamp}-reasoning-compare.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(out), "decision": decision}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
