"""Slice 7.1 experience reasoner failure-path tests."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest

from src.core.exceptions import WandrLLMError
from src.core.llm.client import ChatCompletionResult, LLMUsage  # noqa: F401 — usage types
from src.planner.reasoning.budget import InvocationBudget
from src.planner.reasoning.experience_reasoner import run_experience_reasoner
from src.planner.tools.registry import TOOL_REGISTRY


REPO = Path(__file__).resolve().parents[3]


@pytest.mark.asyncio
async def test_unknown_id_dropped() -> None:
    known = uuid4()
    unknown = uuid4()
    content = (
        '{"priorities":['
        f'{{"place_id":"{known}","priority":"high"}},'
        f'{{"place_id":"{unknown}","priority":"medium"}}'
        "]}"
    )
    with patch(
        "src.planner.reasoning.experience_reasoner.chat_completion",
        new=AsyncMock(
            return_value=ChatCompletionResult(
                content=content,
                usage=LLMUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )
        ),
    ):
        result = await run_experience_reasoner(
            raw_input="photography",
            candidates=[{"id": str(known), "name": "A", "category": "viewpoint"}],
            budget=InvocationBudget(max_invocations=2),
        )
    assert result.skipped is False
    assert known in result.priorities
    assert unknown not in result.priorities
    assert result.dropped_unknown == 1


@pytest.mark.asyncio
async def test_coordinate_item_dropped() -> None:
    known = uuid4()
    content = (
        '{"priorities":['
        f'{{"place_id":"{known}","priority":"high","lat":27.0,"lng":88.0}}'
        "]}"
    )
    with patch(
        "src.planner.reasoning.experience_reasoner.chat_completion",
        new=AsyncMock(
            return_value=ChatCompletionResult(content=content, usage=LLMUsage())
        ),
    ):
        result = await run_experience_reasoner(
            raw_input="x",
            candidates=[{"id": str(known), "name": "A"}],
            budget=InvocationBudget(max_invocations=2),
        )
    assert result.skipped is False
    assert result.priorities == {}
    assert result.dropped_invalid == 1


@pytest.mark.asyncio
async def test_malformed_payload_skipped() -> None:
    with patch(
        "src.planner.reasoning.experience_reasoner.chat_completion",
        new=AsyncMock(
            return_value=ChatCompletionResult(content="not-json", usage=LLMUsage())
        ),
    ):
        result = await run_experience_reasoner(
            raw_input="x",
            candidates=[{"id": str(uuid4()), "name": "A"}],
            budget=InvocationBudget(max_invocations=2),
        )
    assert result.skipped is True
    assert result.reason == "malformed"
    assert result.priorities == {}


@pytest.mark.asyncio
async def test_gateway_error_does_not_swap_models() -> None:
    calls: list[str | None] = []

    async def _fail(*_a, model=None, **_k):
        calls.append(model)
        raise WandrLLMError(code="llm_unavailable", message="down")

    with patch(
        "src.planner.reasoning.experience_reasoner.chat_completion",
        new=_fail,
    ):
        result = await run_experience_reasoner(
            raw_input="x",
            candidates=[{"id": str(uuid4()), "name": "A"}],
            budget=InvocationBudget(max_invocations=2),
        )
    assert result.skipped is True
    assert result.reason == "llm_unavailable"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_deadline_skip() -> None:
    async def _slow(*_a, **_k):
        import asyncio

        await asyncio.sleep(60)
        return ChatCompletionResult(content="{}", usage=LLMUsage())

    with (
        patch(
            "src.planner.reasoning.experience_reasoner.role_deadline_seconds",
            return_value=0.01,
        ),
        patch(
            "src.planner.reasoning.experience_reasoner.chat_completion",
            new=_slow,
        ),
    ):
        result = await run_experience_reasoner(
            raw_input="x",
            candidates=[{"id": str(uuid4()), "name": "A"}],
            budget=InvocationBudget(max_invocations=2),
        )
    assert result.skipped is True
    assert result.reason == "deadline"


@pytest.mark.asyncio
async def test_budget_cap_one_keeps_reasoner_slot() -> None:
    budget = InvocationBudget(max_invocations=1)
    with patch(
        "src.planner.reasoning.experience_reasoner.chat_completion",
        new=AsyncMock(
            return_value=ChatCompletionResult(
                content='{"priorities":[]}', usage=LLMUsage()
            )
        ),
    ):
        first = await run_experience_reasoner(
            raw_input="x",
            candidates=[{"id": str(uuid4()), "name": "A"}],
            budget=budget,
        )
        second = await run_experience_reasoner(
            raw_input="x",
            candidates=[{"id": str(uuid4()), "name": "B"}],
            budget=budget,
        )
    assert first.reason in {"ok", "malformed"}
    assert second.skipped is True
    assert second.reason == "budget"


def test_registry_does_not_contain_reasoner() -> None:
    assert "experience_reasoner" not in TOOL_REGISTRY
    assert "propose_priorities" not in TOOL_REGISTRY


def test_package_does_not_import_litellm() -> None:
    root = REPO / "src" / "planner" / "reasoning"
    forbidden = {"litellm", "groq", "openai"}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden
