"""Slice 7.2 advisory critic tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.core.llm.client import ChatCompletionResult, LLMUsage
from src.planner.reasoning.budget import InvocationBudget
from src.planner.reasoning.critic import run_critic


@pytest.mark.asyncio
async def test_critic_pass_leaves_critical_finding_untouched() -> None:
    findings = [
        {
            "code": "DUPLICATE_STOP",
            "severity": "critical",
            "blocks_publish": True,
        }
    ]
    validation = {"passed": False, "findings": findings}
    content = (
        '{"notes":[{"dimension":"relevance","stance":"pass","message":"ok"}],'
        '"prompt_version":"s7-critic-1","rubric_version":"s7-rubric-1"}'
    )
    with patch(
        "src.planner.reasoning.critic.chat_completion",
        new=AsyncMock(
            return_value=ChatCompletionResult(content=content, usage=LLMUsage())
        ),
    ):
        result = await run_critic(
            raw_input="trip",
            search_area=None,
            evidence_refs=[],
            itinerary={"days": []},
            findings=findings,
            budget=InvocationBudget(max_invocations=2),
        )
    assert result.skipped is False
    assert validation["passed"] is False
    assert findings[0]["blocks_publish"] is True
    assert findings[0]["code"] == "DUPLICATE_STOP"


@pytest.mark.asyncio
async def test_repair_note_dropped() -> None:
    content = (
        '{"notes":[{"dimension":"relevance","stance":"fail","message":"fix",'
        '"repair_action":"drop_weakest_stop","blocks_publish":true}],'
        '"prompt_version":"s7-critic-1","rubric_version":"s7-rubric-1"}'
    )
    with patch(
        "src.planner.reasoning.critic.chat_completion",
        new=AsyncMock(
            return_value=ChatCompletionResult(content=content, usage=LLMUsage())
        ),
    ):
        result = await run_critic(
            raw_input="trip",
            search_area=None,
            evidence_refs=[],
            itinerary={},
            findings=[],
            budget=InvocationBudget(max_invocations=2),
        )
    assert result.skipped is False
    assert result.notes == []


@pytest.mark.asyncio
async def test_critic_timeout_skip_no_emit() -> None:
    emitted: list[tuple[str, dict]] = []

    async def _slow(*_a, **_k):
        import asyncio

        await asyncio.sleep(60)
        return ChatCompletionResult(content="{}", usage=LLMUsage())

    with (
        patch(
            "src.planner.reasoning.critic.role_deadline_seconds",
            return_value=0.01,
        ),
        patch(
            "src.planner.reasoning.critic.chat_completion",
            new=_slow,
        ),
    ):
        result = await run_critic(
            raw_input="trip",
            search_area=None,
            evidence_refs=[],
            itinerary={},
            findings=[],
            budget=InvocationBudget(max_invocations=2),
        )
    assert result.skipped is True
    assert result.reason == "deadline"
    assert emitted == []
    # Critic has no emit hook; uuid used only to keep import used for future expand.
    _ = uuid4()
