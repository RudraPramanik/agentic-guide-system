"""Phase transition + orchestration bookkeeping tests (step 5.5)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.planner.tools import registry
from src.planner.tools.registry import (
    TOOL_REGISTRY,
    _make_test_state,
    apply_tool_result,
    execute_tool,
    get_tools_for_phase,
    maybe_transition_phase,
)
from src.planner.tools.schemas import AgentPhase, BuildRouteIn, ToolResult


def test_helpers_exported() -> None:
    assert callable(registry.maybe_transition_phase)
    assert callable(registry.get_tools_for_phase)
    assert callable(registry.apply_tool_result)
    assert callable(registry._make_test_state)
    assert get_tools_for_phase(AgentPhase.DISCOVER)


def test_rank_places_success_advances_to_plan() -> None:
    state = _make_test_state(agent_phase=AgentPhase.DISCOVER)
    result = ToolResult(ok=True, data={"ranked_pois": []})
    apply_tool_result(state, "rank_places", result, duration_ms=1.0)
    maybe_transition_phase(state, "rank_places", result)
    assert state["agent_phase"] == AgentPhase.PLAN
    assert state["tool_loop_count"] == 1
    assert len(state["tool_trace"]) == 1


def test_validate_fail_with_replan_budget_enters_replan() -> None:
    state = _make_test_state(
        agent_phase=AgentPhase.VALIDATE,
        replan_loop_count=0,
        max_replan_attempts=2,
    )
    result = ToolResult(
        ok=False,
        code="validation_failed",
        data={"last_validate_ok": False, "errors": ["too_far"]},
    )
    apply_tool_result(state, "validate_itinerary", result)
    maybe_transition_phase(state, "validate_itinerary", result)
    assert state["agent_phase"] == AgentPhase.REPLAN
    assert state["replan_loop_count"] == 1
    assert state["abort_triggered"] is False


def test_validate_fail_replan_exhausted_aborts_wrap_up() -> None:
    state = _make_test_state(
        agent_phase=AgentPhase.VALIDATE,
        replan_loop_count=2,
        max_replan_attempts=2,
    )
    result = ToolResult(ok=False, code="validation_failed", data={"errors": ["x"]})
    apply_tool_result(state, "validate_itinerary", result)
    maybe_transition_phase(state, "validate_itinerary", result)
    assert state["agent_phase"] == AgentPhase.WRAP_UP
    assert state["abort_triggered"] is True


@pytest.mark.asyncio
async def test_wrong_phase_rejects_without_calling_fn() -> None:
    state = _make_test_state(agent_phase=AgentPhase.DISCOVER, route=["keep"])
    original = TOOL_REGISTRY["build_route"].fn
    spy = AsyncMock(return_value=ToolResult(ok=True, data={"route": ["mutated"]}))
    TOOL_REGISTRY["build_route"].fn = spy
    try:
        result = await execute_tool("build_route", BuildRouteIn(), state=state)
        assert result.ok is False
        assert result.code == "precondition_failed"
        spy.assert_not_awaited()
        apply_tool_result(state, "build_route", result)
        assert state["route"] == ["keep"]
        assert state["tool_loop_count"] == 1
    finally:
        TOOL_REGISTRY["build_route"].fn = original


@pytest.mark.asyncio
async def test_unknown_tool_does_not_increment_loop_count() -> None:
    state = _make_test_state()
    result = await execute_tool("nope", {})
    assert result.code == "unknown_tool"
    apply_tool_result(state, "nope", result)
    assert state["tool_loop_count"] == 0
    assert len(state["tool_trace"]) == 1


def test_apply_tool_result_copies_fusion_diagnostics_to_trace() -> None:
    state = _make_test_state(agent_phase=AgentPhase.DISCOVER)
    diag = {
        "mode": "hybrid_rrf",
        "collection": "places_v2",
        "sparse_enabled": True,
        "fused_place_ids": ["a"],
        "dense_place_ids": ["a"],
        "sparse_place_ids": ["b"],
        "top_k": 5,
    }
    result = ToolResult(
        ok=True,
        data={
            "candidate_pois": [{"place_id": "a"}],
            "used_geo_fallback": False,
            "fusion_diagnostics": diag,
        },
    )
    apply_tool_result(state, "search_places", result, duration_ms=12.0)
    assert len(state["tool_trace"]) == 1
    assert state["tool_trace"][0]["diagnostics"] == diag
    assert state["candidate_pois"] == [{"place_id": "a"}]
    assert "fusion_diagnostics" not in state


def test_apply_tool_result_without_diagnostics_keeps_trace_shape() -> None:
    state = _make_test_state(agent_phase=AgentPhase.DISCOVER)
    result = ToolResult(ok=True, data={"ranked_pois": []})
    apply_tool_result(state, "rank_places", result)
    assert len(state["tool_trace"]) == 1
    assert state["tool_trace"][0].get("diagnostics") is None
    assert "fusion_diagnostics" not in state
