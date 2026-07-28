"""P3: readiness uses live is_qdrant_available()."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.destinations.service import DestinationService


@pytest.mark.asyncio
async def test_get_readiness_reaches_ready_when_qdrant_up() -> None:
    svc = DestinationService(AsyncMock())
    dest = SimpleNamespace(
        id=uuid.uuid4(), place_count=144, enriched_count=140, indexed_count=140
    )
    svc.repo.get_by_id = AsyncMock(return_value=dest)
    with patch("src.destinations.service.is_qdrant_available", return_value=True):
        out = await svc.get_readiness(dest.id)
        assert out.tier == "ready"


@pytest.mark.asyncio
async def test_get_readiness_zeros_indexed_pct_when_qdrant_down() -> None:
    svc = DestinationService(AsyncMock())
    dest = SimpleNamespace(
        id=uuid.uuid4(), place_count=144, enriched_count=140, indexed_count=140
    )
    svc.repo.get_by_id = AsyncMock(return_value=dest)
    with patch("src.destinations.service.is_qdrant_available", return_value=False):
        out = await svc.get_readiness(dest.id)
        assert out.indexed_pct == 0.0


@pytest.mark.asyncio
async def test_get_readiness_gated_fixture_drops_tier_when_qdrant_down() -> None:
    svc = DestinationService(AsyncMock())
    dest = SimpleNamespace(
        id=uuid.uuid4(), place_count=80, enriched_count=40, indexed_count=80
    )
    svc.repo.get_by_id = AsyncMock(return_value=dest)
    with patch("src.destinations.service.is_qdrant_available", return_value=True):
        up = await svc.get_readiness(dest.id)
        assert up.tier == "ready"
    with patch("src.destinations.service.is_qdrant_available", return_value=False):
        down = await svc.get_readiness(dest.id)
        assert down.indexed_pct == 0.0
        assert down.tier in ("limited", "sparse")
