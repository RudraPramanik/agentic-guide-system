"""Golden-dataset eval runner.

Usage:
  python scripts/run_evals.py --destination darjeeling
  python scripts/run_evals.py --destination darjeeling --update-baseline
  python scripts/run_evals.py --destination darjeeling --fixtures-only
  python scripts/run_evals.py --destination darjeeling --replay

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

from src.evaluation.golden import GoldenCaseError, load_golden_cases  # noqa: E402
from src.evaluation.judge.judge import DEFAULT_SAMPLE_SIZE, judge_case  # noqa: E402
from src.evaluation.metrics import duplicate_stop_count  # noqa: E402
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
    try:
        cases = load_golden_cases(folder)
    except GoldenCaseError as exc:
        raise SystemExit(str(exc)) from exc
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
    replay: bool = False,
) -> tuple[dict[str, Any], str]:
    if fixtures_only:
        fix = _load_fixture(case["id"])
        if fix is None:
            raise SystemExit(f"missing fixture for {case['id']}")
        return fix, "fixture"

    from src.config import get_settings

    settings = get_settings()
    if not replay and not (settings.LLM_API_KEY or "").strip():
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
    try:
        result = await svc.generate(
            destination_id=dest_id,
            raw_input=str(case["raw_input"]),
            base_lat=float(case.get("base_lat") or 27.037),
            base_lng=float(case.get("base_lng") or 88.263),
            session_id=f"eval-{case['id']}-{uuid4().hex[:8]}",
            routing=FakeRoutingProvider(),
        )
    except Exception as exc:
        from src.core.exceptions import WandrLLMError

        if replay and isinstance(exc, WandrLLMError) and exc.code == "replay_miss":
            raise SystemExit(exc.message) from exc
        raise
    if replay:
        from src.core.llm.client import replay_misses

        missed = replay_misses()
        if missed:
            raise SystemExit(f"replay_miss: {missed[0]}")
    return result, "generate"


def _is_quarantined(case: dict[str, Any]) -> bool:
    return case.get("quarantined") is True


def gate_pass_rate(results: list[dict[str, Any]]) -> float:
    gate = [row for row in results if not _is_quarantined(row)]
    if not gate:
        return 1.0
    return sum(1 for row in gate if row.get("passed")) / len(gate)


def _stop_place_ids(state: dict[str, Any]) -> list[str]:
    itinerary = state.get("itinerary") or {}
    days = itinerary.get("days") if isinstance(itinerary, dict) else None
    if not isinstance(days, list):
        return []
    ids: list[str] = []
    for day in days:
        if not isinstance(day, dict):
            continue
        for stop in day.get("stops") or []:
            if isinstance(stop, dict) and stop.get("place_id"):
                ids.append(str(stop["place_id"]))
    return ids


def _load_tolerances() -> dict[str, Any]:
    path = ROOT / "evals" / "baselines" / "tolerances.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _diff_baseline(
    run: dict[str, Any],
    baseline: dict[str, Any],
) -> list[str]:
    diffs: list[str] = []
    base_cases = {c["id"]: c for c in baseline.get("cases") or []}
    for case in run.get("cases") or []:
        if _is_quarantined(case):
            continue
        cid = case["id"]
        prev = base_cases.get(cid)
        if prev is None:
            continue  # new case — not a regression
        if prev.get("passed") and not case.get("passed"):
            diffs.append(
                f"REGRESSION {cid}: was pass, now fail reasons={case.get('reasons')}"
            )
    return diffs


def _tolerance_failures(
    metrics: dict[str, Any],
    tolerances: dict[str, Any],
) -> list[str]:
    """Hard-fail only metrics listed with a numeric baseline.

    A metric is worse than ``baseline - tolerance`` when a higher value is
    worse and the run exceeds that floor, or when a lower value is worse and
    the run falls below that floor. Unlisted metrics never change the exit.
    """
    lines: list[str] = []
    for name, band in tolerances.items():
        if name.startswith("_") or not isinstance(band, dict):
            continue
        if "baseline" not in band or band.get("baseline") is None:
            continue
        if name not in metrics or metrics[name] is None:
            continue
        baseline = float(band["baseline"])
        tolerance = float(band.get("tolerance") or 0)
        floor = baseline - tolerance
        value = float(metrics[name])
        higher_is_worse = bool(band.get("higher_is_worse", True))
        worse = value > floor if higher_is_worse else value < floor
        if worse:
            lines.append(
                f"TOLERANCE {name}: value={value} baseline={baseline} "
                f"tolerance={tolerance}"
            )
    return lines


def finish_run(
    report: dict[str, Any],
    *,
    baseline_path: Path,
    tolerances: dict[str, Any],
    update_baseline: bool,
    allow_new_fails: bool,
) -> tuple[int, list[str]]:
    """Compare a report to the baseline. Writes the baseline only when asked."""
    messages: list[str] = []
    if update_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        messages.append(f"updated baseline {baseline_path}")
        return 0, messages

    before = baseline_path.read_bytes() if baseline_path.is_file() else None
    results = list(report.get("cases") or [])
    gate = [row for row in results if not _is_quarantined(row)]

    if not baseline_path.is_file():
        messages.append(
            f"warning: no baseline at {baseline_path}; "
            "run with --update-baseline to freeze"
        )
        code = 0 if all(row["passed"] for row in gate) else 1
        return code, messages

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if before is not None and baseline_path.read_bytes() != before:
        raise RuntimeError("baseline changed before the gate decision")
    if baseline.get("case_set_hash") != report.get("case_set_hash"):
        messages.append(
            "warning: stale baseline case-set hash "
            f"(baseline={baseline.get('case_set_hash')} "
            f"run={report.get('case_set_hash')})"
        )
    diffs = _diff_baseline(report, baseline)
    diffs.extend(_tolerance_failures(report.get("metrics") or {}, tolerances))
    if diffs:
        return 1, diffs
    failed = [row for row in gate if not row.get("passed")]
    if failed and not allow_new_fails:
        return 1, [f"FAIL {row['id']}: {row.get('reasons')}" for row in failed]
    messages.append(f"ok pass_rate={report['pass_rate']:.2f}")
    if before is not None and baseline_path.read_bytes() != before:
        raise RuntimeError("baseline bytes changed without --update-baseline")
    return 0, messages


async def _amain(args: argparse.Namespace) -> int:
    if args.replay:
        from src.core.llm.client import use_llm_replay

        with use_llm_replay("replay"):
            return await _run_suite(args)
    return await _run_suite(args)


async def _run_suite(args: argparse.Namespace) -> int:
    dest = args.destination
    cases = _load_cases(dest)
    results: list[dict[str, Any]] = []
    judgments: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        state, mode = await _generate_or_fixture(
            case,
            fixtures_only=args.fixtures_only,
            replay=args.replay,
        )
        verdict = score_case(state, case)
        if index < DEFAULT_SAMPLE_SIZE:
            itinerary = state.get("itinerary") if isinstance(state, dict) else {}
            judgment = await judge_case(
                case,
                itinerary if isinstance(itinerary, dict) else {},
                sample_index=index,
                sample_size=DEFAULT_SAMPLE_SIZE,
            )
            judgments.append({"id": case["id"], **judgment})
        quarantined = _is_quarantined(case)
        results.append(
            {
                "id": case["id"],
                "passed": verdict.passed,
                "reasons": list(verdict.reasons),
                "mode": mode,
                "quarantined": quarantined,
                "duplicate_stop_count": duplicate_stop_count(_stop_place_ids(state)),
            }
        )

    gate = [row for row in results if not row["quarantined"]]
    quarantined_rows = [row for row in results if row["quarantined"]]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha = _git_sha()
    report = {
        "destination": dest,
        "timestamp": ts,
        "git_sha": sha,
        "case_set_hash": _case_set_hash(cases),
        "pass_rate": gate_pass_rate(results),
        "cases": results,
        "quarantined_cases": quarantined_rows,
        "judge": judgments,
        "metrics": {
            "duplicate_stop_count": sum(row["duplicate_stop_count"] for row in gate),
        },
    }
    runs_dir = ROOT / "evals" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_path = runs_dir / f"{ts}-{sha}.json"
    run_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {run_path}")

    code, messages = finish_run(
        report,
        baseline_path=ROOT / "evals" / "baselines" / f"{dest}.json",
        tolerances=_load_tolerances(),
        update_baseline=args.update_baseline,
        allow_new_fails=args.allow_new_fails,
    )
    stream = sys.stdout if code == 0 else sys.stderr
    for line in messages:
        print(line, file=stream)
    return code


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
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Serve LLM calls from evals/replay. Does not call the provider.",
    )
    args = parser.parse_args()
    import asyncio

    raise SystemExit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()
