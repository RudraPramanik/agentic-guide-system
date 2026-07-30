"""accept_partial — REPLAN; signal abort toward WRAP_UP."""

from __future__ import annotations

from typing import Any

from src.planner.tools.schemas import AcceptPartialIn, ToolResult


async def run(
    inp: AcceptPartialIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    _ = inp
    _ = ctx
    _ = state
    return ToolResult(
        ok=True,
        data={"abort_triggered": True},
        message="accepting partial itinerary",
    )
