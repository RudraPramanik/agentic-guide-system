"""Tests for P4 execute_tool stub envelope."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from src.planner.tools.registry import execute_tool
from src.planner.tools.schemas import ToolResult


class Empty(BaseModel):
    pass


@pytest.mark.asyncio
async def test_unknown_tool_soft_failure():
    result = await execute_tool("no_such_tool", Empty())
    assert isinstance(result, ToolResult)
    assert result.ok is False
    assert result.code == "unknown_tool"


@pytest.mark.asyncio
async def test_unknown_tool_with_dict_input():
    result = await execute_tool("also_missing", {})
    assert result.ok is False
    assert result.code == "unknown_tool"
