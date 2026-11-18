"""Rows 4.4 and 4.7: return legs on route tools, findings merge, replan force."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.planner.graph.messages import build_agent_messages
from src.planner.tools import build_route as build_route_mod
from src.planner.tools import orchestration
from src.planner.tools import reoptimize_routes as reopt_mod
from src.planner.tools import validate_itinerary as validate_mod
from src.planner.tools.orchestration import (
    apply_tool_result,
    choose_replan_tool,
    maybe_transition_phase,
    run_stuck_detector,
)
from src.planner.tools.registry import _make_test_state
from src.planner.tools.schemas import (
    AgentPhase,
    BuildRouteIn,
    ReoptimizeRoutesIn,
    ToolResult,
    ValidateItineraryIn,
)
from src.travel_engine.route_optimizer import optimize_route
from tests.travel_engine.fake_routing import FakeRoutingProvider


def _ranked(name: str) -> dict:
    return {
        "place": {
            "id": str(uuid4()),
            "name": name,
            "category": "museum",
            "enriched_tags": ["cultural"],
            "lat": 27.04,
            "lng": 88.26,
        },
        "score": 1.0,
        "score_breakdown": {},
    }


def _settings(*, engine: bool) -> SimpleNamespace:
    return SimpleNamespace(
        TRAVEL_ENGINE_V2_ENABLED=engine,
        VALIDATOR_V2_ENFORCE=False,
        PLANNER_MAX_TOOL_CALLS=40,
        PLANNER_MAX_REPLAN_ATTEMPTS=2,
        PLANNER_AGENT_PHASE_STUCK_LIMIT=3,
    )


def _ctx() -> SimpleNamespace:
    return SimpleNamespace(
        routing=FakeRoutingProvider(default_duration_min=10, default_distance_km=1.0),
        base_lat=27.03,
        base_lng=88.26,
    )


@pytest.mark.asyncio
async def test_build_route_flag_off_stays_open_jaw() -> None:
    state = {
        "ranked_pois": [_ranked("Museum")],
        "preferences": {"interests": ["cultural"], "days": 1},
        "base_lat": 27.03,
        "base_lng": 88.26,
    }
    with (
        patch.object(build_route_mod, "get_settings", return_value=_settings(engine=False)),
        patch.object(build_route_mod, "optimize_route", wraps=optimize_route) as spy,
    ):
        result = await build_route_mod.run(BuildRouteIn(), ctx=_ctx(), state=state)
    assert result.ok is True
    assert spy.call_args.kwargs["return_to_base"] is False
    day = result.data["route"][0]
    assert day["return_polyline"] is None
    assert day["total_travel_min"] == 10


@pytest.mark.asyncio
async def test_build_route_and_reoptimize_flag_on_include_return() -> None:
    state = {
        "ranked_pois": [_ranked("Museum")],
        "preferences": {"interests": ["cultural"], "days": 1},
        "base_lat": 27.03,
        "base_lng": 88.26,
    }
    settings = _settings(engine=True)
    with (
        patch.object(build_route_mod, "get_settings", return_value=settings),
        patch.object(build_route_mod, "optimize_route", wraps=optimize_route) as spy,
    ):
        built = await build_route_mod.run(BuildRouteIn(), ctx=_ctx(), state=state)
        reopt = await reopt_mod.run(ReoptimizeRoutesIn(), ctx=_ctx(), state=state)
    assert built.ok is True
    assert reopt.ok is True
    assert all(call.kwargs["return_to_base"] is True for call in spy.call_args_list)
    assert built.data["route"][0]["total_travel_min"] == 20
    assert built.data["route"][0]["return_polyline"]
    assert reopt.data["route"][0]["total_travel_min"] == 20


def _shadow_state() -> dict:
    return {
        "schedule": [
            {
                "stops": [
                    {
                        "place_id": str(uuid4()),
                        "name": "Later",
                        "lat": 27.03,
                        "lng": 88.26,
                        "category": "attraction",
                        "suggested_start_time": "10:00",
                        "visit_duration_min": 30,
                        "score": 1.0,
                        "enriched_tags": ["photography"],
                        "evidence_count": 1,
                        "opening_hours_status": "verified",
                        "opening_open": "08:00",
                        "opening_close": "18:00",
                    },
                    {
                        "place_id": str(uuid4()),
                        "name": "Earlier",
                        "lat": 27.04,
                        "lng": 88.27,
                        "category": "attraction",
                        "suggested_start_time": "09:00",
                        "visit_duration_min": 30,
                        "score": 1.0,
                        "enriched_tags": ["photography"],
                        "evidence_count": 1,
                        "opening_hours_status": "verified",
                        "opening_open": "08:00",
                        "opening_close": "18:00",
                    },
                ],
                "total_travel_min": 10,
            }
        ],
        "route": [],
    }


@pytest.mark.asyncio
async def test_findings_merge_follows_engine_flag_and_enforce_stays_shadow() -> None:
    with patch.object(
        validate_mod, "get_settings", return_value=_settings(engine=False)
    ):
        result = await validate_mod.run(ValidateItineraryIn(), state=_shadow_state())
    assert result.ok is True
    assert result.data["v2_findings"]
    off = _make_test_state(agent_phase=AgentPhase.VALIDATE)
    with patch.object(orchestration, "get_settings", return_value=_settings(engine=False)):
        apply_tool_result(off, "validate_itinerary", result)
    assert "v2_findings" not in off
    on = _make_test_state(agent_phase=AgentPhase.VALIDATE)
    with patch.object(orchestration, "get_settings", return_value=_settings(engine=True)):
        apply_tool_result(on, "validate_itinerary", result)
    assert on["v2_findings"] == result.data["v2_findings"]


def test_blocking_finding_forces_existing_tool() -> None:
    state = _make_test_state(
        agent_phase=AgentPhase.VALIDATE,
        replan_loop_count=0,
        max_replan_attempts=2,
    )
    state["v2_findings"] = [
        {
            "code": "OPENING_HOURS_CONFLICT",
            "blocks_publish": True,
            "suggested_action": "reoptimize_routes",
        }
    ]
    result = ToolResult(ok=False, code="validation_failed", data={"errors": ["x"]})
    with patch.object(orchestration, "get_settings", return_value=_settings(engine=True)):
        maybe_transition_phase(state, "validate_itinerary", result)
    assert state["agent_phase"] == AgentPhase.REPLAN
    assert state["force_next_tool"] == "reoptimize_routes"


def test_unknown_action_is_ignored() -> None:
    assert choose_replan_tool(
        [{"code": "OPENING_HOURS_UNKNOWN", "blocks_publish": False, "suggested_action": None}]
    ) is None
    assert choose_replan_tool(
        [{"code": "DUPLICATE_STOP", "blocks_publish": True, "suggested_action": "invent_tool"}]
    ) is None
    state = _make_test_state(
        agent_phase=AgentPhase.VALIDATE,
        replan_loop_count=0,
        max_replan_attempts=2,
    )
    state["v2_findings"] = [
        {"code": "DUPLICATE_STOP", "blocks_publish": True, "suggested_action": "invent_tool"}
    ]
    result = ToolResult(ok=False, code="validation_failed", data={"errors": ["x"]})
    with patch.object(orchestration, "get_settings", return_value=_settings(engine=True)):
        maybe_transition_phase(state, "validate_itinerary", result)
    assert state.get("force_next_tool") in (None, "")


def test_unchanged_signature_forces_accept_partial() -> None:
    state = _make_test_state(
        agent_phase=AgentPhase.VALIDATE,
        replan_loop_count=0,
        max_replan_attempts=2,
    )
    state["v2_findings"] = [
        {
            "code": "EXCESSIVE_TRAVEL_TIME",
            "blocks_publish": False,
            "suggested_action": "drop_weakest_stop",
        }
    ]
    state["route"] = [
        {
            "dropped_stops": [
                {"place_id": "abc", "reason": "exceeded_max_daily_travel"}
            ]
        }
    ]
    result = ToolResult(ok=False, code="validation_failed", data={"errors": ["x"]})
    settings = _settings(engine=True)
    with patch.object(orchestration, "get_settings", return_value=settings):
        maybe_transition_phase(state, "validate_itinerary", result)
        assert state["force_next_tool"] == "drop_weakest_stop"
        state["agent_phase"] = AgentPhase.VALIDATE
        state["force_next_tool"] = None
        maybe_transition_phase(state, "validate_itinerary", result)
    assert state["force_next_tool"] == "accept_partial"


def test_exhausted_replan_does_not_force_a_repair() -> None:
    state = _make_test_state(
        agent_phase=AgentPhase.VALIDATE,
        replan_loop_count=2,
        max_replan_attempts=2,
    )
    state["v2_findings"] = [
        {
            "code": "OPENING_HOURS_CONFLICT",
            "blocks_publish": True,
            "suggested_action": "reoptimize_routes",
        }
    ]
    result = ToolResult(ok=False, code="validation_failed", data={"errors": ["x"]})
    with patch.object(orchestration, "get_settings", return_value=_settings(engine=True)):
        maybe_transition_phase(state, "validate_itinerary", result)
    assert state["agent_phase"] == AgentPhase.WRAP_UP
    assert state["abort_triggered"] is True
    assert state.get("force_next_tool") is None


def test_flag_off_replan_message_prefers_expand() -> None:
    state = {
        "agent_phase": AgentPhase.REPLAN,
        "route": [{"dropped_stops": [{"place_id": "abc", "reason": "exceeded_max_daily_travel"}]}],
    }
    with patch("src.planner.graph.messages.get_settings", return_value=_settings(engine=False)):
        text = build_agent_messages(state)[0]["content"]
    assert "expand_poi_search" in text.lower()


def test_flag_on_replan_message_names_tool_and_reason() -> None:
    state = {
        "agent_phase": AgentPhase.REPLAN,
        "v2_findings": [
            {
                "code": "EXCESSIVE_TRAVEL_TIME",
                "blocks_publish": False,
                "suggested_action": "drop_weakest_stop",
            }
        ],
        "route": [
            {
                "dropped_stops": [
                    {"place_id": "abc", "reason": "exceeded_max_daily_travel"}
                ]
            }
        ],
    }
    with patch("src.planner.graph.messages.get_settings", return_value=_settings(engine=True)):
        text = build_agent_messages(state)[0]["content"]
    assert "drop_weakest_stop" in text
    assert "exceeded_max_daily_travel" in text


def test_flag_on_stuck_replan_forces_accept_partial() -> None:
    state = _make_test_state(agent_phase=AgentPhase.REPLAN, stuck_cycles=2)
    state["stuck_fingerprint"] = "replan|c=0|r=0|rt=0|s=0|v="
    with patch.object(orchestration, "get_settings", return_value=_settings(engine=True)):
        run_stuck_detector(state)
    assert state["force_next_tool"] == "accept_partial"
    assert state["agent_phase"] == AgentPhase.REPLAN
    assert "phase_stuck_replan_accept_partial" in state["warnings"]
