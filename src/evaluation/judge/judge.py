"""Offline sampled judge. Calls only the LLM gateway. Never gates a trip."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from src.config import get_settings
from src.core.llm.client import chat_completion
from src.evaluation.judge.dimensions import PROMPT_TEXT, PROMPT_VERSION, RUBRIC_VERSION
from src.evaluation.judge.schema import parse_judgment

DEFAULT_SAMPLE_SIZE = 1


def _messages(case: dict[str, Any], itinerary: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": PROMPT_TEXT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "prompt_version": PROMPT_VERSION,
                    "rubric_version": RUBRIC_VERSION,
                    "case_id": case.get("id"),
                    "raw_input": case.get("raw_input"),
                    "itinerary": itinerary,
                },
                default=str,
            ),
        },
    ]


async def judge_case(
    case: dict[str, Any],
    itinerary: dict[str, Any] | None = None,
    *,
    sample_index: int = 0,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> dict[str, Any]:
    """Judge one case when the flag is on and the sample includes it.

    Failure returns ``judge_unavailable`` and does not raise. The caller keeps
    the deterministic gate result it already computed.
    """
    settings = get_settings()
    if not settings.EVALUATION_JUDGE_ENABLED:
        return {"status": "skipped"}
    if sample_index >= sample_size:
        return {"status": "not_sampled"}
    try:
        result = await asyncio.wait_for(
            chat_completion(
                _messages(case, itinerary or {}),
                response_format={"type": "json_object"},
            ),
            timeout=float(settings.EVALUATION_JUDGE_TIMEOUT_SECONDS),
        )
        parsed = parse_judgment(json.loads(result.content or ""))
    except Exception:
        return {"status": "judge_unavailable"}
    if parsed is None:
        return {"status": "judge_unavailable", "reason": "invalid_schema"}
    return {"status": "ok", "judgment": parsed}
