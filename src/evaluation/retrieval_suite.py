"""Offline retrieval recall suite. Recorded rankings only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.evaluation.metrics import retrieval_recall_at_k

RECALL_K = 10
RECALL_FLOOR = 0.80
METRIC_NAME = "retrieval_recall@10"


def load_retrieval_cases(folder: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not data.get("id"):
            raise ValueError(f"{path.name}: invalid retrieval case")
        must = data.get("must_include") or []
        retrieved = data.get("retrieved") or []
        if not isinstance(must, list) or not must:
            raise ValueError(f"{path.name}: must_include")
        if not isinstance(retrieved, list):
            raise ValueError(f"{path.name}: retrieved")
        cases.append(data)
    return cases


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def run_retrieval_suite(
    folder: Path,
    baseline_path: Path,
    *,
    update_baseline: bool = False,
) -> tuple[int, list[str]]:
    cases = load_retrieval_cases(folder)
    if not cases:
        return 1, [f"no cases in {folder}"]
    messages: list[str] = []
    recalls: list[float] = []
    for case in cases:
        recall = retrieval_recall_at_k(
            [str(item) for item in case["retrieved"]],
            [str(item) for item in case["must_include"]],
            RECALL_K,
        )
        recalls.append(recall)
        if recall < RECALL_FLOOR:
            messages.append(f"fail {case['id']}: recall={recall}")
        else:
            messages.append(f"pass {case['id']}: recall={recall}")
    if any(value < RECALL_FLOOR for value in recalls):
        return 1, messages
    mean = _mean(recalls)
    if update_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(
            json.dumps({METRIC_NAME: mean}, indent=2) + "\n",
            encoding="utf-8",
        )
        messages.append(f"ok {METRIC_NAME}={mean}")
        return 0, messages
    if not baseline_path.is_file():
        messages.append(f"missing baseline {baseline_path.name}")
        return 1, messages
    stored = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
    baseline = float(stored.get(METRIC_NAME, 1.0))
    if mean + 1e-12 < baseline:
        messages.append(f"{METRIC_NAME}={mean} baseline={baseline}")
        return 1, messages
    if mean + 1e-12 < RECALL_FLOOR:
        messages.append(f"{METRIC_NAME}={mean}")
        return 1, messages
    messages.append(f"ok {METRIC_NAME}={mean}")
    return 0, messages
