"""ask_clarification — DISCOVER; signals needs_clarification for graph exit."""

from __future__ import annotations

from typing import Any

from src.planner.tools.schemas import AskClarificationIn, ToolResult


_DESTINATION_QUESTION = (
    "which destination",
    "what destination",
    "which city",
    "which region",
    "where would you like",
    "where do you want",
)


def _destination_bound(ctx: Any, state: Any) -> bool:
    if ctx is not None and getattr(ctx, "destination_id", None):
        return True
    if isinstance(state, dict) and state.get("destination_id"):
        return True
    return False


async def run(
    inp: AskClarificationIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    question = (inp.question or "").strip() or "Could you clarify your trip preferences?"
    folded = question.lower()
    if _destination_bound(ctx, state) and any(
        phrase in folded for phrase in _DESTINATION_QUESTION
    ):
        return ToolResult(
            ok=False,
            code="destination_already_bound",
            message="destination is already selected",
        )
    return ToolResult(
        ok=True,
        data={
            "needs_clarification": True,
            "clarification_question": question,
        },
    )
