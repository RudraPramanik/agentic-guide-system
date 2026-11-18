"""Service flag routing for readiness. No database."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.destinations.repository import DestinationRepository
from src.destinations.service import DestinationService
from src.places.repository import PlaceRepository


def _dest() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        place_count=144,
        enriched_count=0,
        indexed_count=0,
    )


@pytest.mark.asyncio
async def test_flag_off_does_not_load_places(monkeypatch) -> None:
    dest = _dest()
    called = {"list": 0}

    async def get_by_id(self, destination_id):  # noqa: ARG001
        return dest

    async def list_all(self, destination_id):  # noqa: ARG001
        called["list"] += 1
        return []

    monkeypatch.setattr(DestinationRepository, "get_by_id", get_by_id)
    monkeypatch.setattr(PlaceRepository, "list_all_for_destination", list_all)
    monkeypatch.setattr("src.destinations.service.is_qdrant_available", lambda: False)
    monkeypatch.setattr(
        "src.destinations.service.get_settings",
        lambda: SimpleNamespace(READINESS_V2_ENABLED=False),
    )
    service = DestinationService(AsyncMock())
    first = await service.get_readiness(dest.id, days=1)
    second = await service.get_readiness(dest.id, days=3)
    assert called["list"] == 0
    assert first.tier == second.tier == "limited"
    assert first.score == second.score
    assert first.place_count == 144


@pytest.mark.asyncio
async def test_flag_on_uses_usable_count(monkeypatch) -> None:
    dest = _dest()
    rows = []
    for index in range(10):
        rows.append(
            SimpleNamespace(
                id=uuid.UUID(int=index + 1),
                name=f"Place {index}",
                category=("monastery", "viewpoint", "museum")[index % 3],
                osm_id=f"n{index}",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                location=object(),
            )
        )

    async def get_by_id(self, destination_id):  # noqa: ARG001
        return dest

    async def list_all(self, destination_id):  # noqa: ARG001
        return rows

    monkeypatch.setattr(DestinationRepository, "get_by_id", get_by_id)
    monkeypatch.setattr(PlaceRepository, "list_all_for_destination", list_all)
    monkeypatch.setattr(
        "src.destinations.service.to_shape",
        lambda _location: SimpleNamespace(y=27.0, x=88.0),
    )
    monkeypatch.setattr(
        "src.destinations.service.get_settings",
        lambda: SimpleNamespace(
            READINESS_V2_ENABLED=True,
            READINESS_MIN_USABLE_PLACES_PER_DAY=4,
            READINESS_MIN_CATEGORIES=3,
            READINESS_MIN_CLUSTERS_MULTI_DAY=2,
            PLANNER_ABSOLUTE_MIN_PLACES=10,
        ),
    )
    service = DestinationService(AsyncMock())
    result = await service.get_readiness(dest.id, days=3)
    assert result.tier == "limited"
    assert result.place_count == 10
    assert result.enriched_pct == 0.0
    assert result.indexed_pct == 0.0


@pytest.mark.asyncio
async def test_days_below_one_is_rejected(monkeypatch) -> None:
    dest = _dest()

    async def get_by_id(self, destination_id):  # noqa: ARG001
        return dest

    monkeypatch.setattr(DestinationRepository, "get_by_id", get_by_id)
    service = DestinationService(AsyncMock())
    with pytest.raises(ValueError):
        await service.get_readiness(dest.id, days=0)
