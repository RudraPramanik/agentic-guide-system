"""Golden-dataset eval runner.

Usage:
  python scripts/run_evals.py --destination darjeeling
  python scripts/run_evals.py --destination darjeeling --update-baseline
  python scripts/run_evals.py --destination darjeeling --fixtures-only

Loads cases from evals/golden/<destination>/*.json, scores via
src.evaluation.scorers.score_case, writes evals/runs/<ts>-<sha>.json,
diffs against evals/baselines/<destination>.json.

With empty LLM_API_KEY (or --fixtures-only), uses evals/fixtures/<case-id>.json
instead of PlannerService.generate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation.scorers import score_case  # noqa: E402


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or "unknown"
    except Exception:
        return "unknown"


def _case_set_hash(cases: list[dict[str, Any]]) -> str:
    blob = json.dumps(
        sorted(c["id"] for c in cases),
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def _load_cases(dest: str) -> list[dict[str, Any]]:
    folder = ROOT / "evals" / "golden" / dest
    if not folder.is_dir():
        raise SystemExit(f"missing golden folder: {folder}")
    cases: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            raise SystemExit(f"invalid JSON in {path.name}: {e}") from e
        if not isinstance(data, dict):
            raise SystemExit(f"case must be object: {path.name}")
        for key in ("id", "destination", "raw_input"):
            if key not in data:
                raise SystemExit(f"{path.name}: missing required field '{key}'")
        assertions = data.get("assertions")
        if not isinstance(assertions, dict) or not assertions:
            raise SystemExit(f"{path.name}: assertions must be a non-empty object")
        cases.append(data)
    if not cases:
        raise SystemExit(f"no cases in {folder}")
    return cases


def _load_fixture(case_id: str) -> dict[str, Any] | None:
    path = ROOT / "evals" / "fixtures" / f"{case_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


async def _generate_or_fixture(
    case: dict[str, Any],
    *,
    fixtures_only: bool,
) -> tuple[dict[str, Any], str]:
    if fixtures_only:
        fix = _load_fixture(case["id"])
        if fix is None:
            raise SystemExit(f"missing fixture for {case['id']}")
        return fix, "fixture"

    from src.config import get_settings

    settings = get_settings()
    if not (settings.LLM_API_KEY or "").strip():
        fix = _load_fixture(case["id"])
        if fix is None:
            raise SystemExit(
                f"LLM_API_KEY empty and no fixture for {case['id']}"
            )
        return fix, "fixture"

    from tests.travel_engine.fake_routing import FakeRoutingProvider
    from src.planner.service import PlannerService
    from src.search.client import ensure_places_collection
    from src.search.embeddings import ensure_embedding_model_loaded

    # Lifespan is not running under the CLI — make Qdrant/embeddings available for real retrieval.
    await ensure_places_collection()
    await ensure_embedding_model_loaded()

    dest_id = case.get("destination_id")
    if not dest_id:
        raise SystemExit(f"{case['id']}: destination_id required for live generate")
    svc = PlannerService()
    result = await svc.generate(
        destination_id=dest_id,
        raw_input=str(case["raw_input"]),
        base_lat=float(case.get("base_lat") or 27.037),
        base_lng=float(case.get("base_lng") or 88.263),
        session_id=f"eval-{case['id']}-{uuid4().hex[:8]}",
        routing=FakeRoutingProvider(),
    )
    return result, "generate"


def _diff_baseline(
    run: dict[str, Any],
    baseline: dict[str, Any],
) -> list[str]:
    diffs: list[str] = []
    base_cases = {c["id"]: c for c in baseline.get("cases") or []}
    for case in run.get("cases") or []:
        cid = case["id"]
        prev = base_cases.get(cid)
        if prev is None:
            continue  # new case — not a regression
        if prev.get("passed") and not case.get("passed"):
            diffs.append(
                f"REGRESSION {cid}: was pass, now fail reasons={case.get('reasons')}"
            )
    return diffs


async def _amain(args: argparse.Namespace) -> int:
    dest = args.destination
    cases = _load_cases(dest)
    results: list[dict[str, Any]] = []
    for case in cases:
        state, mode = await _generate_or_fixture(
            case, fixtures_only=args.fixtures_only
        )
        verdict = score_case(state, case)
        results.append(
            {
                "id": case["id"],
                "passed": verdict.passed,
                "reasons": list(verdict.reasons),
                "mode": mode,
            }
        )

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha = _git_sha()
    report = {
        "destination": dest,
        "timestamp": ts,
        "git_sha": sha,
        "case_set_hash": _case_set_hash(cases),
        "pass_rate": (
            sum(1 for r in results if r["passed"]) / len(results) if results else 0.0
        ),
        "cases": results,
    }
    runs_dir = ROOT / "evals" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_path = runs_dir / f"{ts}-{sha}.json"
    run_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {run_path}")

    baseline_path = ROOT / "evals" / "baselines" / f"{dest}.json"
    if args.update_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"updated baseline {baseline_path}")
        return 0

    if not baseline_path.is_file():
        print(
            f"warning: no baseline at {baseline_path}; "
            "run with --update-baseline to freeze",
            file=sys.stderr,
        )
        return 0 if all(r["passed"] for r in results) else 1

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("case_set_hash") != report["case_set_hash"]:
        print(
            "warning: stale baseline case-set hash "
            f"(baseline={baseline.get('case_set_hash')} run={report['case_set_hash']})",
            file=sys.stderr,
        )
    diffs = _diff_baseline(report, baseline)
    if diffs:
        for d in diffs:
            print(d, file=sys.stderr)
        return 1
    failed = [r for r in results if not r["passed"]]
    if failed and not args.allow_new_fails:
        for r in failed:
            print(f"FAIL {r['id']}: {r['reasons']}", file=sys.stderr)
        return 1
    print(f"ok pass_rate={report['pass_rate']:.2f}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", default="darjeeling")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument(
        "--fixtures-only",
        action="store_true",
        help="Never call PlannerService; use evals/fixtures only",
    )
    parser.add_argument(
        "--allow-new-fails",
        action="store_true",
        help="Only exit non-zero on baseline regressions (not fresh fails)",
    )
    args = parser.parse_args()
    import asyncio

    raise SystemExit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()
