"""Generate and check_readiness forward the trip day count."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from src.destinations.readiness import resolve_trip_days
from src.planner.service import _bind_known_destination
from src.planner.tools.check_readiness import run
from src.planner.tools.schemas import CheckReadinessIn


def test_omitted_generate_days_resolve_to_three() -> None:
    assert resolve_trip_days(None) == 3
    assert resolve_trip_days(3) == 3


class _Session:
    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_check_readiness_forwards_state_days(monkeypatch) -> None:
    seen: list[int] = []

    class FakeService:
        def __init__(self, session) -> None:  # noqa: ARG002
            return None

        async def get_readiness(self, destination_id, days=1):  # noqa: ARG002
            seen.append(days)
            return SimpleNamespace(
                score=0.1,
                tier="sparse",
                place_count=1,
                enriched_pct=0.0,
                indexed_pct=0.0,
                message="sparse",
            )

    monkeypatch.setattr(
        "src.planner.tools.check_readiness.DestinationService",
        FakeService,
    )
    ctx = SimpleNamespace(destination_id=uuid.uuid4(), db=object())
    result = await run(CheckReadinessIn(), ctx=ctx, state={"days": 3})
    assert seen == [3]
    assert result.ok is True
    assert result.data["warning"]
    assert set(result.data) == {
        "readiness_score",
        "tier",
        "place_count",
        "enriched_pct",
        "indexed_pct",
        "warning",
    }


@pytest.mark.asyncio
async def test_check_readiness_uses_context_days_when_state_omits_them(monkeypatch) -> None:
    seen: list[int] = []

    class FakeService:
        def __init__(self, session) -> None:  # noqa: ARG002
            return None

        async def get_readiness(self, destination_id, days=1):  # noqa: ARG002
            seen.append(days)
            return SimpleNamespace(
                score=0.9,
                tier="ready",
                place_count=20,
                enriched_pct=1.0,
                indexed_pct=1.0,
                message=None,
            )

    monkeypatch.setattr(
        "src.planner.tools.check_readiness.DestinationService",
        FakeService,
    )
    ctx = SimpleNamespace(destination_id=uuid.uuid4(), db=object(), readiness_days=3)
    result = await run(CheckReadinessIn(), ctx=ctx, state={})
    assert seen == [3]
    assert result.ok is True
    assert result.data["warning"] is None


@pytest.mark.asyncio
async def test_bind_passes_three_when_generate_omits_days(monkeypatch) -> None:
    seen: list[int] = []

    class FakeService:
        def __init__(self, session) -> None:  # noqa: ARG002
            return None

        async def get_by_id(self, destination_id):  # noqa: ARG002
            return SimpleNamespace(name="Darjeeling")

        async def get_readiness(self, destination_id, days=1):  # noqa: ARG002
            seen.append(days)
            return SimpleNamespace(score=0.4)

    monkeypatch.setattr("src.destinations.service.DestinationService", FakeService)
    monkeypatch.setattr(
        "src.core.database.session.AsyncSessionLocal",
        lambda: _Session(),
    )
    state: dict = {}
    await _bind_known_destination(state, uuid.uuid4(), days=None)
    assert seen == [3]
    assert state["readiness_score"] == 0.4
    assert state["destination_name"] == "Darjeeling"
