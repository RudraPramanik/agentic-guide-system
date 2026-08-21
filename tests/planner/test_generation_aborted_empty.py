"""Defaults, stuck abort, and empty build_route for generation_aborted fix."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.exceptions import WandrLLMError
from src.planner.graph.nodes.agent import _default_tool_for_state, agent_node
from src.planner.tools.build_route import run as build_route_run
from src.planner.tools.orchestration import run_stuck_detector
from src.planner.tools.registry import _make_test_state
from src.planner.tools.schemas import AgentPhase, BuildRouteIn, ToolContext
from tests.travel_engine.fake_routing import FakeRoutingProvider


def test_default_tool_empty_discover_is_check_readiness() -> None:
    assert _default_tool_for_state({"agent_phase": AgentPhase.DISCOVER}) == (
        "check_readiness"
    )


def test_default_tool_after_readiness_is_search_places() -> None:
    state = {
        "agent_phase": AgentPhase.DISCOVER,
        "readiness_score": 0.6,
        "candidate_pois": [],
    }
    assert _default_tool_for_state(state) == "search_places"


def test_default_tool_plan_with_route_is_build_schedule() -> None:
    state = {
        "agent_phase": AgentPhase.PLAN,
        "route": [{"ordered": [{"id": "p1"}]}],
    }
    assert _default_tool_for_state(state) == "build_schedule"


@pytest.mark.asyncio
async def test_llm_error_after_readiness_synthesizes_search_places() -> None:
    settings = MagicMock()
    settings.PLANNER_MAX_TOOL_CALLS = 12
    state = {
        "agent_phase": AgentPhase.DISCOVER,
        "readiness_score": 0.618,
        "candidate_pois": [],
        "tool_loop_count": 1,
        "warnings": [],
        "llm_retry_count": 0,
        "raw_input": "3 day trip",
    }
    with (
        patch(
            "src.planner.graph.nodes.agent.chat_with_tools",
            new=AsyncMock(side_effect=WandrLLMError()),
        ),
        patch(
            "src.planner.graph.nodes.agent.get_settings",
            return_value=settings,
        ),
    ):
        out = await agent_node(state, {})
    names = [c.get("name") for c in out.get("pending_tool_calls") or []]
    assert names == ["search_places"]
    assert "agent_no_tool_call_default_used" in (out.get("warnings") or [])


def test_stuck_discover_without_pois_aborts_wrap_up() -> None:
    settings = MagicMock()
    settings.PLANNER_AGENT_PHASE_STUCK_LIMIT = 2
    state = _make_test_state(agent_phase=AgentPhase.DISCOVER)
    state["candidate_pois"] = []
    with patch(
        "src.planner.tools.orchestration.get_settings",
        return_value=settings,
    ):
        run_stuck_detector(state)
        run_stuck_detector(state)
    assert state["agent_phase"] == AgentPhase.WRAP_UP
    assert state["abort_triggered"] is True
    assert any("phase_stuck" in str(w) for w in (state.get("warnings") or []))
    assert state["agent_phase"] != AgentPhase.PLAN


@pytest.mark.asyncio
async def test_build_route_empty_places_is_not_ok() -> None:
    ctx = ToolContext(
        destination_id=uuid4(),
        base_lat=27.0,
        base_lng=88.0,
        routing=FakeRoutingProvider(),
    )
    result = await build_route_run(
        BuildRouteIn(),
        ctx,
        {"ranked_pois": [], "candidate_pois": [], "days": 3},
    )
    assert result.ok is False
    assert result.code == "no_ranked_places"
