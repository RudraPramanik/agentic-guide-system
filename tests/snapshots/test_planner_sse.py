"""Frozen planner SSE framing. The graph is not compiled."""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock

from tests.snapshots.compare import assert_fixture, load_request
from tests.snapshots.normalize import normalize
from tests.snapshots.seed import seed_destination

_PROGRESS = (
    ("preferences_done", {
        "interests": ["nature"],
        "budget": "moderate",
        "days": 2,
        "include_offbeat": False,
        "include_trekking": False,
    }),
    ("phase_changed", {"phase": "discover"}),
    ("tool_done", {"name": "search_places", "ok": True, "code": None, "ms": 1}),
    ("tool_batch_done", {}),
    ("itinerary_done", {"days": []}),
)


def _parse_sse(text: str) -> list[dict]:
    frames: list[dict] = []
    for block in text.split("\n\n"):
        if "event:" not in block:
            continue
        event_name = None
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
        frames.append({"event": event_name, "data": normalize(data)})
    return frames


def _script(events: tuple[tuple[str, dict], ...], dest_id: str):
    async def _generate(**kwargs):
        on_event = kwargs["on_event"]
        for name, data in events:
            on_event(name, data)
        return {
            "destination_id": dest_id,
            "schedule": [],
            "plan_complete": False,
            "abort_triggered": False,
        }

    return _generate


async def _ready_destination(db_session):
    return await seed_destination(
        db_session,
        name="Snapshot Generate",
        osm_place_id="relation/snapshot-generate",
        place_count=12,
    )


@pytest.mark.asyncio
async def test_sse_progress_sequence_matches_fixture(client, db_session, monkeypatch) -> None:
    dest = await _ready_destination(db_session)
    monkeypatch.setattr(
        "src.planner.router.PlannerService.generate",
        AsyncMock(side_effect=_script(_PROGRESS, str(dest.id))),
    )
    request = load_request("generate.json")

    response = await client.post(
        "/api/v1/planner/generate",
        json={"destination_id": str(dest.id), "raw_input": request["raw_input"]},
    )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/event-stream")
    assert response.headers.get("cache-control") == "no-cache"
    assert response.headers.get("x-accel-buffering") == "no"
    frames = _parse_sse(response.text)
    assert [frame["event"] for frame in frames] == [
        "preferences_done",
        "phase_changed",
        "tool_done",
        "tool_batch_done",
        "itinerary_done",
    ]
    assert frames[-1]["event"] == "itinerary_done"
    assert response.text.count("event: itinerary_done") == 1
    assert "tool_started" not in response.text
    assert "validation_done" not in response.text
    assert_fixture("sse-progress.json", {"events": frames})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_name", "data", "fixture_name"),
    [
        ("error", {"code": "generation_timeout"}, "sse-error.json"),
        ("clarification_needed", {"question": "Which city?"}, "sse-clarification.json"),
    ],
)
async def test_sse_single_terminal_matches_fixture(
    client, db_session, monkeypatch, event_name, data, fixture_name
) -> None:
    dest = await _ready_destination(db_session)
    monkeypatch.setattr(
        "src.planner.router.PlannerService.generate",
        AsyncMock(side_effect=_script(((event_name, data),), str(dest.id))),
    )
    request = load_request("generate.json")

    response = await client.post(
        "/api/v1/planner/generate",
        json={"destination_id": str(dest.id), "raw_input": request["raw_input"]},
    )

    assert response.status_code == 200
    frames = _parse_sse(response.text)
    assert [frame["event"] for frame in frames] == [event_name]
    assert response.text.count(f"event: {event_name}") == 1
    assert_fixture(fixture_name, {"events": frames})


@pytest.mark.asyncio
async def test_sse_second_terminal_is_dropped(client, db_session, monkeypatch) -> None:
    dest = await _ready_destination(db_session)
    monkeypatch.setattr(
        "src.planner.router.PlannerService.generate",
        AsyncMock(
            side_effect=_script(
                (
                    ("itinerary_done", {"days": []}),
                    ("error", {"code": "generation_timeout"}),
                ),
                str(dest.id),
            )
        ),
    )
    request = load_request("generate.json")

    response = await client.post(
        "/api/v1/planner/generate",
        json={"destination_id": str(dest.id), "raw_input": request["raw_input"]},
    )

    assert response.status_code == 200
    frames = _parse_sse(response.text)
    terminal_names = [frame["event"] for frame in frames]
    assert terminal_names.count("itinerary_done") + terminal_names.count("error") == 1
    assert_fixture("sse-double-terminal.json", {"events": frames})


@pytest.mark.asyncio
async def test_generate_floor_is_409_without_sse(client, db_session, monkeypatch) -> None:
    dest = await seed_destination(
        db_session,
        name="Snapshot Empty",
        osm_place_id="relation/snapshot-empty",
        place_count=0,
    )
    generate = AsyncMock()
    monkeypatch.setattr("src.planner.router.PlannerService.generate", generate)
    request = load_request("generate.json")

    response = await client.post(
        "/api/v1/planner/generate",
        json={"destination_id": str(dest.id), "raw_input": request["raw_input"]},
    )

    assert response.status_code == 409
    assert "event:" not in response.text
    generate.assert_not_called()
    assert_fixture("generate-floor.json", response.json())
