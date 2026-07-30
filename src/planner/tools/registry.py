"""Tool registry skeleton — unknown tools soft-fail. Full PHASE_TOOLS is P5."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from src.planner.tools.schemas import ToolResult

# P4: empty / placeholder keys only — no real tool bodies.
_TOOL_REGISTRY: dict[str, Any] = {}


async def execute_tool(
    name: str,
    input: BaseModel | dict,  # noqa: A002 — matches step4 locked signature
    ctx: object | None = None,
) -> ToolResult:
    """Dispatch by name. Unknown → ok=False; never raise."""
    if name not in _TOOL_REGISTRY:
        return ToolResult(
            ok=False,
            code="unknown_tool",
            message=f"unknown tool: {name}",
            data=None,
        )
    # Placeholder path for future P5 registrations — unreachable with empty registry.
    return ToolResult(ok=False, code="not_implemented", message=name)
