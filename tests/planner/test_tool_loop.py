"""Integration coverage for the planner tool loop (P5.13)."""

from __future__ import annotations

import asyncio
import inspect
import re
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.core.llm.client import LLMToolResponse
from src.planner.service import PlannerService
from src.planner.tools.registry import TOOL_REGISTRY, _make_test_state, execute_tool
from src.planner.tools.schemas import AgentPhase, BuildRouteIn, FinishPlanIn, ToolResult
from tests.travel_engine.fake_routing import FakeRoutingProvider

_DEST_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_DEST_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

_STOP = {
    "place_id": str(uuid4()),
    "lat": 27.04,
    "lng": 88.26,
    "suggested_start_time": "09:00",
    "name": "Test Stop",
}


def _day(n: int) -> dict[str, Any]:
    return {
        "day": n,
        "stops": [{**_STOP, "suggested_start_time": f"{8 + n:02d}:00"}],
    }


def _schedule(days: int = 3) -> list[dict[str, Any]]:
    return [_day(i) for i in range(1, days + 1)]


def _tc(name: str, arguments_json: str = "{}") -> dict[str, Any]:
    return {"name": name, "arguments_json": arguments_json, "id": name}


def _canned_tool(name: str, state: Any = None) -> ToolResult:
    if name == "check_readiness":
        return ToolResult(ok=True, data={"readiness_score": 0.9, "tier": "ready"})
    if name == "search_places":
        return ToolResult(
            ok=True,
            data={"candidate_pois": [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}]},
        )
    if name == "rank_places":
        return ToolResult(
            ok=True,
            data={"ranked_pois": [{"id": "p1"}, {"id": "p2"}, {"id": "p3"}]},
        )
    if name == "build_route":
        return ToolResult(ok=True, data={"route": _schedule(3)})
    if name == "build_schedule":
        return ToolResult(ok=True, data={"schedule": _schedule(3)})
    if name == "validate_itinerary":
        return ToolResult(
            ok=True,
            data={"validation_result": {"passed": True}, "last_validate_ok": True},
        )
    if name == "finish_plan":
        sched = (state or {}).get("schedule") if isinstance(state, dict) else None
        sched = sched or _schedule(3)
        return ToolResult(
            ok=True,
            data={
                "plan_complete": True,
                "itinerary": {"schedule": sched, "days": len(sched)},
            },
        )
    if name == "ask_clarification":
        return ToolResult(
            ok=True,
            data={
                "needs_clarification": True,
                "clarification_question": "How many days?",
            },
        )
    if name == "reoptimize_routes":
        return ToolResult(ok=True, data={"route": _schedule(3)})
    if name == "accept_partial":
        return ToolResult(ok=True, data={"route": _schedule(2)})
    if name == "drop_weakest_stop":
        return ToolResult(ok=True, data={"route": _schedule(2)})
    if name == "expand_poi_search":
        return ToolResult(ok=True, data={"candidate_pois": [{"id": "p4"}]})
    return ToolResult(ok=False, code="not_implemented", message=name)


@pytest.fixture
def patched_tools():
    originals: dict[str, Any] = {}
    for name in list(TOOL_REGISTRY.keys()):
        originals[name] = TOOL_REGISTRY[name].fn

        async def _fn(
            inp: Any = None,
            ctx: Any = None,
            state: Any = None,
            *,
            _n: str = name,
        ) -> ToolResult:
            _ = inp
            return _canned_tool(_n, state)

        TOOL_REGISTRY[name].fn = _fn
    yield
    for name, fn in originals.items():
        TOOL_REGISTRY[name].fn = fn


def _scripted_chat_with_tools(script: list[str | None]) -> AsyncMock:
    queue = list(script)

    async def _side_effect(messages, tools, tool_choice="auto", **kwargs):
        _ = messages, tools, tool_choice, kwargs
        if not queue:
            return LLMToolResponse(tool_calls=[], content="done")
        nxt = queue.pop(0)
        if nxt is None:
            return LLMToolResponse(tool_calls=[], content="no tool")
        return LLMToolResponse(tool_calls=[_tc(nxt)], content=None)

    return AsyncMock(side_effect=_side_effect)


def _test_settings(
    *,
    max_tools: int = 12,
    timeout: float = 45.0,
    stuck: int = 3,
) -> MagicMock:
    settings = MagicMock()
    settings.PLANNER_MAX_TOOL_CALLS = max_tools
    settings.PLANNER_MAX_REPLAN_ATTEMPTS = 2
    settings.PLANNER_GENERATION_TIMEOUT_SECONDS = timeout
    settings.PLANNER_AGENT_PHASE_STUCK_LIMIT = stuck
    settings.LLM_MODEL = "test"
    return settings


async def _noop_prefs(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "days": 3,
        "budget": "budget",
        "interests": ["photography"],
        "include_offbeat": True,
        "include_trekking": False,
        "llm_retry_count": int(state.get("llm_retry_count") or 0),
    }


async def _noop_narrative(state: dict[str, Any]) -> dict[str, Any]:
    schedule = state.get("schedule") or _schedule(3)
    return {
        "itinerary": {
            "days": [
                {
                    "day": d["day"],
                    "title": f"Day {d['day']}",
                    "narrative": "ok",
                    "stops": d.get("stops"),
                }
                for d in schedule
            ],
            "schedule": schedule,
        }
    }


async def _noop_eval(state: dict[str, Any]) -> dict[str, Any]:
    _ = state
    return {}


@pytest.fixture
def graph_mocks():
    """Rebuild compiled graph with bookend mocks; mock service eval."""
    import src.planner.graph.builder as builder

    mock_eval = AsyncMock(side_effect=_noop_eval)
    with ExitStack() as stack:
        stack.enter_context(patch.object(builder, "parse_preferences", _noop_prefs))
        stack.enter_context(patch.object(builder, "write_narrative", _noop_narrative))
        stack.enter_context(patch.object(builder, "record_evaluation", _noop_eval))
        stack.enter_context(
            patch("src.planner.service.record_evaluation", mock_eval)
        )
        builder._compiled = None
        yield mock_eval
        builder._compiled = None


async def _generate(
    *,
    script: list[str | None],
    mock_eval: AsyncMock,
    destination_id: UUID = _DEST_A,
    settings: MagicMock | None = None,
    executor_wrapper=None,
) -> dict[str, Any]:
    import src.planner.graph.builder as builder

    settings = settings or _test_settings()
    chat_mock = _scripted_chat_with_tools(script)
    builder._compiled = None

    with ExitStack() as stack:
        stack.enter_context(
            patch("src.planner.graph.nodes.agent.chat_with_tools", chat_mock)
        )
        stack.enter_context(
            patch("src.planner.graph.nodes.agent.get_settings", return_value=settings)
        )
        stack.enter_context(
            patch(
                "src.planner.tools.orchestration.get_settings",
                return_value=settings,
            )
        )
        stack.enter_context(
            patch("src.planner.service.get_settings", return_value=settings)
        )
        stack.enter_context(patch("src.planner.service.record_evaluation", mock_eval))
        if executor_wrapper is not None:
            stack.enter_context(
                patch.object(builder, "tool_executor_node", executor_wrapper)
            )
        builder._compiled = None
        try:
            return await PlannerService().generate(
                destination_id=destination_id,
                raw_input="3 days offbeat photography budget",
                base_lat=27.04,
                base_lng=88.26,
                session_id="test-session",
                routing=FakeRoutingProvider(),
            )
        finally:
            builder._compiled = None


@pytest.mark.asyncio
async def test_happy_path_discover_to_wrap_up(patched_tools, graph_mocks):
    final = await _generate(
        script=[
            "check_readiness",
            "search_places",
            "rank_places",
            "build_route",
            "build_schedule",
            "validate_itinerary",
            "finish_plan",
        ],
        mock_eval=graph_mocks,
    )
    assert final.get("plan_complete") is True
    assert int(final.get("tool_loop_count") or 0) <= 8
    for day in final.get("schedule") or []:
        for stop in day.get("stops") or []:
            assert stop.get("suggested_start_time")
    graph_mocks.assert_awaited()


@pytest.mark.asyncio
async def test_validation_fail_enters_replan(patched_tools, graph_mocks):
    originals = {n: TOOL_REGISTRY[n].fn for n in ("validate_itinerary",)}

    async def validate_fail(inp=None, ctx=None, state=None):
        return ToolResult(
            ok=False,
            code="validation_failed",
            data={"errors": ["too_far"], "last_validate_ok": False},
        )

    TOOL_REGISTRY["validate_itinerary"].fn = validate_fail
    try:
        final = await _generate(
            script=[
                "check_readiness",
                "search_places",
                "rank_places",
                "build_route",
                "build_schedule",
                "validate_itinerary",
                "accept_partial",
                "finish_plan",
            ],
            mock_eval=graph_mocks,
        )
        assert int(final.get("replan_loop_count") or 0) <= 2
        assert int(final.get("replan_loop_count") or 0) >= 1
        names = [
            t.get("name")
            for t in (final.get("tool_trace") or [])
            if isinstance(t, dict)
        ]
        assert "validate_itinerary" in names
        assert "accept_partial" in names
    finally:
        for n, fn in originals.items():
            TOOL_REGISTRY[n].fn = fn


@pytest.mark.asyncio
async def test_max_tool_calls_aborts_and_records_eval(patched_tools, graph_mocks):
    final = await _generate(
        script=["check_readiness"] * 20,
        mock_eval=graph_mocks,
        settings=_test_settings(max_tools=2),
    )
    assert final.get("abort_triggered") is True
    graph_mocks.assert_awaited()


@pytest.mark.asyncio
async def test_ask_clarification_exits_without_plan(patched_tools, graph_mocks):
    final = await _generate(script=["ask_clarification"], mock_eval=graph_mocks)
    assert final.get("needs_clarification") is True
    assert not final.get("plan_complete")
    graph_mocks.assert_awaited()


@pytest.mark.asyncio
async def test_finish_plan_blocked_without_validate(patched_tools):
    state = _make_test_state(agent_phase=AgentPhase.WRAP_UP)
    result = await execute_tool("finish_plan", FinishPlanIn(), state=state)
    assert result.ok is False
    assert result.code == "precondition_failed"


@pytest.mark.asyncio
async def test_wrong_phase_tool_not_called(patched_tools):
    state = _make_test_state(agent_phase=AgentPhase.DISCOVER)
    spy = AsyncMock(return_value=ToolResult(ok=True, data={"route": []}))
    original = TOOL_REGISTRY["build_route"].fn
    TOOL_REGISTRY["build_route"].fn = spy
    try:
        result = await execute_tool("build_route", BuildRouteIn(), state=state)
        assert result.ok is False
        assert result.code == "precondition_failed"
        spy.assert_not_awaited()
    finally:
        TOOL_REGISTRY["build_route"].fn = original


@pytest.mark.asyncio
async def test_agent_no_tool_nudge_default_via_executor(patched_tools, graph_mocks):
    import src.planner.graph.builder as builder
    import src.planner.graph.nodes.agent as agent_mod

    assert "execute_tool(" not in inspect.getsource(agent_mod.agent_node)

    calls = {"n": 0}
    seq_after = [
        "search_places",
        "rank_places",
        "build_route",
        "build_schedule",
        "validate_itinerary",
        "finish_plan",
    ]

    async def chat_side(messages, tools, tool_choice="auto", **kwargs):
        _ = messages, tools, tool_choice, kwargs
        calls["n"] += 1
        if calls["n"] <= 2:
            return LLMToolResponse(tool_calls=[], content="no")
        idx = calls["n"] - 3
        if idx < len(seq_after):
            return LLMToolResponse(tool_calls=[_tc(seq_after[idx])], content=None)
        return LLMToolResponse(tool_calls=[_tc("finish_plan")], content=None)

    execute_spy = AsyncMock(side_effect=execute_tool)
    settings = _test_settings()
    builder._compiled = None
    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "src.planner.graph.nodes.agent.chat_with_tools",
                new=AsyncMock(side_effect=chat_side),
            )
        )
        stack.enter_context(
            patch("src.planner.graph.nodes.agent.get_settings", return_value=settings)
        )
        stack.enter_context(
            patch(
                "src.planner.tools.orchestration.get_settings",
                return_value=settings,
            )
        )
        stack.enter_context(
            patch("src.planner.service.get_settings", return_value=settings)
        )
        stack.enter_context(patch("src.planner.service.record_evaluation", graph_mocks))
        stack.enter_context(
            patch("src.planner.graph.nodes.tool_executor.execute_tool", execute_spy)
        )
        final = await PlannerService().generate(
            destination_id=_DEST_A,
            raw_input="x",
            base_lat=1.0,
            base_lng=2.0,
            session_id="s",
            routing=FakeRoutingProvider(),
        )
    builder._compiled = None
    assert execute_spy.await_count >= 1
    assert "agent_no_tool_call_default_used" in (final.get("warnings") or [])
    names = [
        t.get("name") for t in (final.get("tool_trace") or []) if isinstance(t, dict)
    ]
    assert "check_readiness" in names


@pytest.mark.asyncio
async def test_concurrent_generations_isolate_tool_context(patched_tools, graph_mocks):
    """Same compiled graph; two generates must not share ToolContext."""
    import src.planner.graph.builder as builder

    seen: list[UUID] = []
    original = TOOL_REGISTRY["ask_clarification"].fn

    async def tracking_clarify(inp=None, ctx=None, state=None):
        if ctx is not None and getattr(ctx, "destination_id", None) is not None:
            seen.append(ctx.destination_id)
        return _canned_tool("ask_clarification", state)

    TOOL_REGISTRY["ask_clarification"].fn = tracking_clarify
    settings = _test_settings()

    async def chat_always_clarify(messages, tools, tool_choice="auto", **kwargs):
        _ = messages, tools, tool_choice, kwargs
        return LLMToolResponse(tool_calls=[_tc("ask_clarification")], content=None)

    builder._compiled = None
    try:
        with ExitStack() as stack:
            stack.enter_context(
                patch(
                    "src.planner.graph.nodes.agent.chat_with_tools",
                    new=AsyncMock(side_effect=chat_always_clarify),
                )
            )
            stack.enter_context(
                patch(
                    "src.planner.graph.nodes.agent.get_settings",
                    return_value=settings,
                )
            )
            stack.enter_context(
                patch(
                    "src.planner.tools.orchestration.get_settings",
                    return_value=settings,
                )
            )
            stack.enter_context(
                patch("src.planner.service.get_settings", return_value=settings)
            )
            stack.enter_context(
                patch("src.planner.service.record_evaluation", graph_mocks)
            )

            async def run_dest(dest: UUID):
                return await PlannerService().generate(
                    destination_id=dest,
                    raw_input="x",
                    base_lat=1.0,
                    base_lng=2.0,
                    session_id=f"s-{dest}",
                    routing=FakeRoutingProvider(),
                )

            await asyncio.gather(run_dest(_DEST_A), run_dest(_DEST_B))
        assert _DEST_A in seen and _DEST_B in seen
    finally:
        TOOL_REGISTRY["ask_clarification"].fn = original
        builder._compiled = None


@pytest.mark.asyncio
async def test_tool_trace_accumulates_across_cycles(patched_tools, graph_mocks):
    final = await _generate(
        script=[
            "check_readiness",
            "search_places",
            "rank_places",
            "build_route",
            "build_schedule",
            "validate_itinerary",
            "finish_plan",
        ],
        mock_eval=graph_mocks,
    )
    assert len(final.get("tool_trace") or []) >= 4


@pytest.mark.asyncio
async def test_timeout_after_tool_cycle_keeps_trace(patched_tools, graph_mocks):
    import src.planner.graph.builder as builder
    import src.planner.graph.nodes.tool_executor as te

    slept = {"done": False}
    orig = te.tool_executor_node

    async def wrapping(state, config):
        out = await orig(state, config)
        if not slept["done"] and (out.get("tool_trace") or []):
            slept["done"] = True
            await asyncio.sleep(0.2)
        return out

    final = await _generate(
        script=["check_readiness"] * 20,
        mock_eval=graph_mocks,
        settings=_test_settings(timeout=0.05),
        executor_wrapper=wrapping,
    )
    builder._compiled = None
    assert "generation_timeout" in (final.get("errors") or [])
    assert final.get("abort_triggered") is True
    assert len(final.get("tool_trace") or []) >= 1
    graph_mocks.assert_awaited()


@pytest.mark.asyncio
async def test_stuck_detector_aborts_unknown_tool_path(patched_tools, graph_mocks):
    final = await _generate(
        script=["not_a_real_tool"] * 30,
        mock_eval=graph_mocks,
        settings=_test_settings(max_tools=50, stuck=3),
    )
    warnings = final.get("warnings") or []
    assert any("phase_stuck" in str(w) for w in warnings) or final.get("plan_complete")
    assert int(final.get("tool_loop_count") or 0) < 50


def test_import_guards() -> None:
    root = Path(__file__).resolve().parents[2]
    litellm_hits = []
    for path in (root / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"import litellm|from litellm", text):
            if "core" in path.parts and path.name == "client.py":
                continue
            litellm_hits.append(str(path))
    assert litellm_hits == []

    tool_impl = re.compile(
        r"from src\.planner\.tools\.(check_readiness|search_places|rank_places|"
        r"build_route|build_schedule)"
    )
    for path in (root / "src" / "planner" / "graph" / "nodes").rglob("*.py"):
        assert not tool_impl.search(path.read_text(encoding="utf-8")), path

    agent_src = (root / "src" / "planner" / "graph" / "nodes" / "agent.py").read_text(
        encoding="utf-8"
    )
    assert "execute_tool(" not in agent_src
