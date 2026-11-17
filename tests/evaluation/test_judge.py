"""Offline judge schema, flag, failure isolation, and request-path import ban."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.config import get_settings
from src.evaluation.judge.dimensions import PROMPT_VERSION, RUBRIC_VERSION
from src.evaluation.judge.judge import judge_case
from src.evaluation.judge.schema import parse_judgment
from src.evaluation.judge.sheet import validate_review_sheet
from scripts.run_evals import finish_run, gate_pass_rate

ROOT = Path(__file__).resolve().parents[2]


def _valid_payload() -> dict:
    return {
        "model": "nvidia_nim/test",
        "prompt_version": PROMPT_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "relevance": {"passed": True, "note": "matches"},
        "diversity": {"passed": False, "note": "same viewpoint"},
        "narrative": {"passed": True, "note": ""},
    }


def test_schema_accepts_versioned_judgment() -> None:
    parsed = parse_judgment(_valid_payload())
    assert parsed is not None
    assert parsed["prompt_version"] == PROMPT_VERSION
    assert parsed["dimensions"]["diversity"]["passed"] is False


def test_schema_rejects_missing_dimension() -> None:
    payload = _valid_payload()
    del payload["narrative"]
    assert parse_judgment(payload) is None


def test_judge_timeout_setting_defaults_to_fifteen() -> None:
    settings = get_settings()
    assert settings.EVALUATION_JUDGE_ENABLED is False
    assert settings.EVALUATION_JUDGE_TIMEOUT_SECONDS == 15


@pytest.mark.asyncio
async def test_flag_off_makes_no_gateway_call() -> None:
    with patch(
        "src.evaluation.judge.judge.chat_completion",
        new=AsyncMock(),
    ) as chat:
        result = await judge_case({"id": "dar-001", "raw_input": "3 days"})
    assert result["status"] == "skipped"
    chat.assert_not_called()


@pytest.mark.asyncio
async def test_judge_failure_leaves_deterministic_gate_exit(tmp_path: Path) -> None:
    report = {
        "case_set_hash": "abc",
        "pass_rate": gate_pass_rate(
            [{"id": "seed-pass", "passed": True, "quarantined": False}]
        ),
        "cases": [{"id": "seed-pass", "passed": True, "quarantined": False, "reasons": []}],
        "metrics": {},
    }
    baseline = tmp_path / "darjeeling.json"
    baseline.write_text(json.dumps(report), encoding="utf-8")

    class _Enabled:
        EVALUATION_JUDGE_ENABLED = True
        EVALUATION_JUDGE_TIMEOUT_SECONDS = 15

    code_before, _ = finish_run(
        report,
        baseline_path=baseline,
        tolerances={},
        update_baseline=False,
        allow_new_fails=False,
    )
    with (
        patch(
            "src.evaluation.judge.judge.get_settings",
            return_value=_Enabled(),
        ),
        patch(
            "src.evaluation.judge.judge.chat_completion",
            new=AsyncMock(side_effect=RuntimeError("down")),
        ),
    ):
        judged = await judge_case({"id": "dar-001"})
    code_after, _ = finish_run(
        report,
        baseline_path=baseline,
        tolerances={},
        update_baseline=False,
        allow_new_fails=False,
    )
    assert judged["status"] == "judge_unavailable"
    assert code_before == code_after


def test_human_sheet_validates_without_llm() -> None:
    sheet = json.loads((ROOT / "evals" / "human_review" / "example.json").read_text())
    assert validate_review_sheet(sheet) == []


def test_human_sheet_requires_rubric_version() -> None:
    sheet = json.loads((ROOT / "evals" / "human_review" / "example.json").read_text())
    del sheet["rubric_version"]
    assert "missing_rubric_version" in validate_review_sheet(sheet)


def test_request_path_does_not_import_judge() -> None:
    roots = [
        ROOT / "src" / "planner",
        ROOT / "src" / "travel_engine",
        ROOT / "src" / "trips",
    ]
    for folder in roots:
        for path in folder.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert "evaluation.judge" not in text
            assert "src.evaluation.judge" not in text
