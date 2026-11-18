"""Terminal transcript for rows 4.4 and 4.7. Run with pytest -s."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from src.planner.tools.orchestration import choose_replan_tool, maybe_transition_phase
from src.planner.tools.registry import _make_test_state
from src.planner.tools.schemas import AgentPhase, ToolResult
from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.protocols import legs_to_lookup
from src.travel_engine.route_optimizer import optimize_route
from src.travel_engine.travel_rules import BASE_SENTINEL_ID
from tests.travel_engine.fake_routing import FakeRoutingProvider


def _scored(name: str, score: float) -> ScoredPlace:
    return ScoredPlace(
        place=PlaceCandidate(
            id=uuid4(),
            name=name,
            category="attraction",
            enriched_tags=[],
            lat=27.0,
            lng=88.0,
        ),
        score=score,
        score_breakdown={},
    )


def _hop_minutes(result, frm: UUID, to: UUID) -> int:
    leg = legs_to_lookup(result.legs).get((frm, to))
    assert leg is not None
    return leg.duration_min


@pytest.mark.asyncio
async def test_transcript_return_leg_and_replan() -> None:
    places = [_scored("Museum", 3.0), _scored("Park", 2.0)]
    fake = FakeRoutingProvider(default_duration_min=15, default_distance_km=1.0)
    lines: list[str] = []
    for mode in (False, True):
        result = await optimize_route(
            places, 27.03, 88.26, fake, return_to_base=mode
        )
        names = " -> ".join(stop.place.name for stop in result.ordered)
        first = result.ordered[0].place.id
        last = result.ordered[-1].place.id
        outbound = _hop_minutes(result, BASE_SENTINEL_ID, first)
        hops = [
            _hop_minutes(
                result,
                result.ordered[i].place.id,
                result.ordered[i + 1].place.id,
            )
            for i in range(len(result.ordered) - 1)
        ]
        return_min = (
            _hop_minutes(result, last, BASE_SENTINEL_ID) if mode else 0
        )
        reasons = ",".join(item.reason for item in result.dropped_stops) or "none"
        poly = "set" if result.return_polyline else "null"
        lines.append(
            f"mode={'return' if mode else 'open-jaw'} order={names} "
            f"base_to_first={outbound} hops={hops} last_to_base={return_min} "
            f"total={result.total_travel_min} drops={reasons} return_polyline={poly}"
        )

    finding = {
        "code": "OPENING_HOURS_CONFLICT",
        "blocks_publish": True,
        "suggested_action": "reoptimize_routes",
    }
    tool = choose_replan_tool([finding])
    lines.append(f"finding {finding['code']} -> {tool}")
    state = _make_test_state(
        agent_phase=AgentPhase.VALIDATE,
        replan_loop_count=0,
        max_replan_attempts=2,
    )
    state["v2_findings"] = [finding]
    state["route"] = [{"dropped_stops": []}]
    settings = SimpleNamespace(
        TRAVEL_ENGINE_V2_ENABLED=True,
        PLANNER_MAX_TOOL_CALLS=40,
        PLANNER_MAX_REPLAN_ATTEMPTS=2,
    )
    failed = ToolResult(ok=False, code="validation_failed", data={"errors": ["x"]})
    with patch("src.planner.tools.orchestration.get_settings", return_value=settings):
        maybe_transition_phase(state, "validate_itinerary", failed)
        state["agent_phase"] = AgentPhase.VALIDATE
        state["force_next_tool"] = None
        maybe_transition_phase(state, "validate_itinerary", failed)
    lines.append(f"unchanged signature -> {state['force_next_tool']}")
    for line in lines:
        print(line)
    assert lines[0].startswith("mode=open-jaw")
    assert "return_polyline=null" in lines[0]
    assert "return_polyline=set" in lines[1]
    assert lines[2] == "finding OPENING_HOURS_CONFLICT -> reoptimize_routes"
    assert lines[3] == "unchanged signature -> accept_partial"
