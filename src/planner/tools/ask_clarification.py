"""ask_clarification — DISCOVER; signals needs_clarification for graph exit."""

from __future__ import annotations

from typing import Any

from src.planner.tools.schemas import AskClarificationIn, ToolResult


async def run(
    inp: AskClarificationIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = ctx
    _ = state
    question = (inp.question or "").strip() or "Could you clarify your trip preferences?"
    return ToolResult(
        ok=True,
        data={
            "needs_clarification": True,
            "clarification_question": question,
        },
    )
