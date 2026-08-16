"""Cold-path PlannerService.generate emits itinerary_done without cache replay."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.planner.service import PlannerService


@pytest.mark.asyncio
async def test_generate_emits_itinerary_done_on_success() -> None:
    dest_id = uuid4()
    events: list[tuple[str, dict]] = []

    def on_event(event: str, data: dict) -> None:
        events.append((event, data))

    final_state = {
        "destination_id": str(dest_id),
        "plan_complete": True,
        "needs_clarification": False,
        "abort_triggered": False,
        "days": 1,
        "schedule": [
            {
                "day": 1,
                "stops": [
                    {
                        "place_id": str(uuid4()),
                        "order": 1,
                        "travel_time_min": 0,
                        "visit_duration_min": 60,
                    }
                ],
            }
        ],
        "itinerary": {"days": [{"day": 1, "title": "Day 1", "narrative": "Hi"}]},
        "errors": [],
        "warnings": [],
    }

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value=final_state)

    with (
        patch("src.planner.service.get_compiled_graph", return_value=mock_graph),
        patch(
            "src.planner.service.record_evaluation",
            new=AsyncMock(return_value={}),
        ),
        patch("src.planner.service.OsrmRoutingProvider"),
    ):
        result = await PlannerService().generate(
            destination_id=dest_id,
            raw_input="1 day photography trip",
            base_lat=27.0,
            base_lng=88.0,
            session_id="sess-test",
            on_event=on_event,
        )

    terminals = [e for e, _ in events if e in ("itinerary_done", "error", "clarification_needed")]
    assert terminals == ["itinerary_done"]
    payload = next(d for e, d in events if e == "itinerary_done")
    assert payload["days"] == 1
    assert "itinerary" in payload
    assert result["plan_complete"] is True


@pytest.mark.asyncio
async def test_generate_emits_clarification_needed() -> None:
    dest_id = uuid4()
    events: list[tuple[str, dict]] = []

    def on_event(event: str, data: dict) -> None:
        events.append((event, data))

    final_state = {
        "destination_id": str(dest_id),
        "plan_complete": False,
        "needs_clarification": True,
        "clarification_question": "Budget mid or luxury?",
        "schedule": [],
        "itinerary": {},
        "errors": [],
        "warnings": [],
    }

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value=final_state)

    with (
        patch("src.planner.service.get_compiled_graph", return_value=mock_graph),
        patch(
            "src.planner.service.record_evaluation",
            new=AsyncMock(return_value={}),
        ),
        patch("src.planner.service.OsrmRoutingProvider"),
    ):
        await PlannerService().generate(
            destination_id=dest_id,
            raw_input="trip",
            base_lat=27.0,
            base_lng=88.0,
            session_id="sess-test",
            on_event=on_event,
        )

    terminals = [e for e, _ in events if e in ("itinerary_done", "error", "clarification_needed")]
    assert terminals == ["clarification_needed"]
    assert events[-1][1]["question"] == "Budget mid or luxury?"


@pytest.mark.asyncio
async def test_generate_timeout_single_error_terminal() -> None:
    dest_id = uuid4()
    events: list[tuple[str, dict]] = []

    def on_event(event: str, data: dict) -> None:
        events.append((event, data))

    async def _hang(*_a, **_k):
        import asyncio

        await asyncio.sleep(3600)

    mock_graph = MagicMock()
    mock_graph.ainvoke = _hang

    with (
        patch("src.planner.service.get_compiled_graph", return_value=mock_graph),
        patch(
            "src.planner.service.record_evaluation",
            new=AsyncMock(return_value={}),
        ),
        patch("src.planner.service.OsrmRoutingProvider"),
        patch("src.planner.service.get_settings") as mock_settings,
    ):
        settings = MagicMock()
        settings.PLANNER_GENERATION_TIMEOUT_SECONDS = 0.05
        settings.PLANNER_MAX_TOOL_CALLS = 12
        settings.PLANNER_AGENT_PHASE_STUCK_LIMIT = 3
        settings.PLANNER_MAX_REPLAN_ATTEMPTS = 2
        mock_settings.return_value = settings
        await PlannerService().generate(
            destination_id=dest_id,
            raw_input="trip",
            base_lat=27.0,
            base_lng=88.0,
            session_id="sess-test",
            on_event=on_event,
        )

    terminals = [e for e, _ in events if e in ("itinerary_done", "error", "clarification_needed")]
    assert terminals == ["error"]
    assert events[-1][1]["code"] == "generation_timeout"
