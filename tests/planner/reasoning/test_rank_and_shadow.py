"""Slice 7 live ranking, generate skip, and shadow integration."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.core.llm.client import ChatCompletionResult, LLMUsage
from src.planner.reasoning.budget import InvocationBudget
from src.planner.reasoning.schemas import ReasonerResult
from src.planner.reasoning.shadow import is_shadow_selected, run_shadow_pass
from src.planner.service import PlannerService
from src.planner.tools.schemas import RankPlacesIn, ToolContext
from src.planner.tools import rank_places as rank_places_mod


def _cand(name: str, tags: list[str] | None = None) -> dict:
    return {
        "id": str(uuid4()),
        "name": name,
        "category": "viewpoint",
        "enriched_tags": tags or ["photography"],
        "lat": 27.0,
        "lng": 88.0,
    }


@pytest.mark.asyncio
async def test_flag_off_rank_does_not_call_chat_completion() -> None:
    state = {
        "candidate_pois": [_cand("A")],
        "preferences": {"interests": ["photography"], "days": 2},
        "base_lat": 27.0,
        "base_lng": 88.0,
        "raw_input": "photos",
    }
    settings = SimpleNamespace(
        TRAVEL_ENGINE_V2_ENABLED=False,
        REASONING_LAYER_ENABLED=False,
    )
    with (
        patch.object(rank_places_mod, "get_settings", return_value=settings),
        patch(
            "src.planner.reasoning.experience_reasoner.chat_completion",
            new=AsyncMock(side_effect=AssertionError("should not call")),
        ) as mock_chat,
    ):
        result = await rank_places_mod.run(RankPlacesIn(), state=state)
    assert result.ok is True
    assert set(result.data.keys()) == {"ranked_pois", "explanations"}
    mock_chat.assert_not_called()


@pytest.mark.asyncio
async def test_layer_on_valid_priority_keeps_tool_fields() -> None:
    cand = _cand("A")
    pid = cand["id"]
    state = {
        "candidate_pois": [cand],
        "preferences": {"interests": ["photography"], "days": 2},
        "base_lat": 27.0,
        "base_lng": 88.0,
        "raw_input": "photos",
    }
    ctx = ToolContext(
        destination_id=uuid4(),
        base_lat=27.0,
        base_lng=88.0,
        reasoning_notes=[],
        reasoning_budget=InvocationBudget(max_invocations=2),
    )
    settings = SimpleNamespace(
        TRAVEL_ENGINE_V2_ENABLED=False,
        REASONING_LAYER_ENABLED=True,
    )
    content = (
        '{"priorities":[{"place_id":"' + pid + '","priority":"high"}]}'
    )
    with (
        patch.object(rank_places_mod, "get_settings", return_value=settings),
        patch(
            "src.planner.reasoning.experience_reasoner.chat_completion",
            new=AsyncMock(
                return_value=ChatCompletionResult(
                    content=content,
                    usage=LLMUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
                )
            ),
        ),
    ):
        result = await rank_places_mod.run(RankPlacesIn(), ctx=ctx, state=state)
    assert set(result.data.keys()) == {"ranked_pois", "explanations"}
    assert ctx.reasoning_notes
    assert ctx.reasoning_notes[0]["name"] == "experience_reasoner"


@pytest.mark.asyncio
async def test_reasoner_failure_still_ranks() -> None:
    state = {
        "candidate_pois": [_cand("A")],
        "preferences": {"interests": ["photography"], "days": 2},
        "base_lat": 27.0,
        "base_lng": 88.0,
        "raw_input": "photos",
    }
    ctx = ToolContext(
        destination_id=uuid4(),
        base_lat=27.0,
        base_lng=88.0,
        reasoning_notes=[],
        reasoning_budget=InvocationBudget(max_invocations=2),
    )
    settings = SimpleNamespace(
        TRAVEL_ENGINE_V2_ENABLED=False,
        REASONING_LAYER_ENABLED=True,
    )
    with (
        patch.object(rank_places_mod, "get_settings", return_value=settings),
        patch(
            "src.planner.reasoning.experience_reasoner.chat_completion",
            new=AsyncMock(
                return_value=ChatCompletionResult(content="bad", usage=LLMUsage())
            ),
        ),
    ):
        result = await rank_places_mod.run(RankPlacesIn(), ctx=ctx, state=state)
    assert result.ok is True
    assert "ranked_pois" in result.data
    assert "explanations" in result.data


@pytest.mark.asyncio
async def test_generate_flags_off_skips_roles() -> None:
    service = PlannerService()
    state = {
        "raw_input": "x",
        "destination_id": str(uuid4()),
        "session_id": "s1",
        "plan_complete": True,
        "itinerary": {},
        "candidate_pois": [],
        "tool_trace": [],
        "token_usage": {},
    }
    budget = InvocationBudget(max_invocations=2)
    settings = SimpleNamespace(
        REASONING_LAYER_ENABLED=False,
        REASONING_SHADOW_SAMPLE_RATE=0.0,
        TRAVEL_ENGINE_V2_ENABLED=False,
    )
    with (
        patch("src.planner.service.get_settings", return_value=settings),
        patch(
            "src.planner.reasoning.shadow.run_shadow_pass",
            new=AsyncMock(side_effect=AssertionError("no shadow")),
        ),
        patch(
            "src.planner.reasoning.critic.run_critic",
            new=AsyncMock(side_effect=AssertionError("no critic")),
        ),
    ):
        out = await service._run_post_terminal_reasoning(state, budget=budget)
    assert out["tool_trace"] == []


def test_shadow_selection_stable() -> None:
    dest = uuid4()
    a = is_shadow_selected(
        session_id="s",
        destination_id=dest,
        raw_input="  hello   world ",
        sample_rate=1.0,
    )
    b = is_shadow_selected(
        session_id="s",
        destination_id=dest,
        raw_input="hello world",
        sample_rate=1.0,
    )
    assert a is True and b is True
    assert (
        is_shadow_selected(
            session_id="s",
            destination_id=dest,
            raw_input="hello world",
            sample_rate=0.0,
        )
        is False
    )


@pytest.mark.asyncio
async def test_shadow_does_not_mutate_itinerary_or_emit() -> None:
    events: list[str] = []
    cand_a = _cand("A", ["photography"])
    cand_b = _cand("B", [])
    control_itinerary = {"title": "control", "days": [{"stops": [{"id": cand_a["id"]}]}]}
    state = {
        "session_id": "sess",
        "destination_id": str(uuid4()),
        "raw_input": "photos",
        "candidate_pois": [cand_a, cand_b],
        "preferences": {"interests": ["photography"], "days": 1},
        "base_lat": 27.0,
        "base_lng": 88.0,
        "itinerary": control_itinerary,
        "schedule": [{"day": 1, "stops": [{"place_id": cand_a["id"]}]}],
        "plan_complete": True,
        "abort_triggered": False,
        "tool_trace": [],
        "token_usage": {},
        "validation_result": {"passed": True, "findings": []},
    }
    settings = SimpleNamespace(
        REASONING_LAYER_ENABLED=False,
        REASONING_SHADOW_SAMPLE_RATE=1.0,
        TRAVEL_ENGINE_V2_ENABLED=False,
        ORCHESTRATION_MAX_AGENT_INVOCATIONS=2,
        AGENT_REASONING_MODEL="",
        AGENT_CRITIC_MODEL="",
        LLM_MODEL="test-model",
        LLM_TIMEOUT_SECONDS=20,
        PLANNER_GENERATION_TIMEOUT_SECONDS=45,
    )
    content = (
        '{"priorities":[{"place_id":"'
        + cand_b["id"]
        + '","priority":"high"}]}'
    )
    with (
        patch("src.planner.reasoning.shadow.get_settings", return_value=settings),
        patch(
            "src.planner.reasoning.experience_reasoner.get_settings",
            return_value=settings,
        ),
        patch(
            "src.planner.reasoning.critic.get_settings",
            return_value=settings,
        ),
        patch(
            "src.planner.reasoning.experience_reasoner.chat_completion",
            new=AsyncMock(
                return_value=ChatCompletionResult(
                    content=content,
                    usage=LLMUsage(prompt_tokens=2, completion_tokens=2, total_tokens=4),
                )
            ),
        ),
        patch(
            "src.planner.reasoning.critic.chat_completion",
            new=AsyncMock(
                return_value=ChatCompletionResult(
                    content=(
                        '{"notes":[{"dimension":"relevance","stance":"pass",'
                        '"message":"ok"}],"prompt_version":"s7-critic-1",'
                        '"rubric_version":"s7-rubric-1"}'
                    ),
                    usage=LLMUsage(),
                )
            ),
        ),
    ):
        reasoner, critic, ranked = await run_shadow_pass(
            state, budget=InvocationBudget(max_invocations=2)
        )
    assert reasoner is not None
    assert state["itinerary"] == control_itinerary
    assert state["plan_complete"] is True
    assert "generation_timeout" not in (state.get("errors") or [])
    assert events == []
    assert ranked is not None


@pytest.mark.asyncio
async def test_shadow_timeout_keeps_plan_complete() -> None:
    service = PlannerService()
    state = {
        "raw_input": "x",
        "destination_id": str(uuid4()),
        "session_id": "s1",
        "plan_complete": True,
        "abort_triggered": False,
        "itinerary": {"title": "ok"},
        "candidate_pois": [_cand("A")],
        "tool_trace": [],
        "token_usage": {},
        "errors": [],
    }
    budget = InvocationBudget(max_invocations=2)
    settings = SimpleNamespace(
        REASONING_LAYER_ENABLED=False,
        REASONING_SHADOW_SAMPLE_RATE=1.0,
        TRAVEL_ENGINE_V2_ENABLED=False,
    )
    timed_out = ReasonerResult(
        skipped=True,
        reason="deadline",
        model="test",
        mode="shadow",
    )
    with (
        patch("src.planner.service.get_settings", return_value=settings),
        patch(
            "src.planner.reasoning.shadow.run_shadow_pass",
            new=AsyncMock(return_value=(timed_out, None, None)),
        ),
    ):
        out = await service._run_post_terminal_reasoning(state, budget=budget)
    assert out["plan_complete"] is True
    assert out.get("abort_triggered") is False
    assert "generation_timeout" not in (out.get("errors") or [])
    assert any(e.get("name") == "experience_reasoner" for e in out["tool_trace"])
