"""P3: PlaceService.enrich_place contracts (mocked LLM)."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.core.exceptions import WandrLLMError
from src.places.service import PlaceService


@pytest.mark.asyncio
async def test_enrich_place_skips_when_summary_set() -> None:
    svc = PlaceService(AsyncMock())
    svc.repo.update = AsyncMock()
    place = SimpleNamespace(
        id=uuid.uuid4(),
        name="X",
        category="viewpoint",
        tags={},
        summary="already",
    )
    with patch("src.places.service.chat_completion", new=AsyncMock()) as mock_llm:
        assert await svc.enrich_place(place) is None
        assert mock_llm.await_count == 0


@pytest.mark.asyncio
async def test_enrich_place_returns_none_on_wandr_llm_error() -> None:
    svc = PlaceService(AsyncMock())
    svc.repo.update = AsyncMock()
    place = SimpleNamespace(
        id=uuid.uuid4(), name="Y", category="viewpoint", tags={}, summary=None
    )
    with patch(
        "src.places.service.chat_completion",
        new=AsyncMock(side_effect=WandrLLMError(code="llm_unavailable", message="boom")),
    ):
        assert await svc.enrich_place(place) is None
        assert svc.repo.update.await_count == 0


@pytest.mark.asyncio
async def test_enrich_place_returns_none_on_malformed_json() -> None:
    svc = PlaceService(AsyncMock())
    svc.repo.update = AsyncMock()
    place = SimpleNamespace(
        id=uuid.uuid4(), name="M", category="viewpoint", tags={}, summary=None
    )
    with patch(
        "src.places.service.chat_completion",
        new=AsyncMock(return_value="not even json"),
    ):
        assert await svc.enrich_place(place) is None
        assert svc.repo.update.await_count == 0


@pytest.mark.asyncio
async def test_enrich_place_filters_vocab_and_never_writes_tags() -> None:
    svc = PlaceService(AsyncMock())
    svc.repo.update = AsyncMock()
    place = SimpleNamespace(
        id=uuid.uuid4(), name="Z", category="viewpoint", tags={}, summary=None
    )
    with patch(
        "src.places.service.chat_completion",
        new=AsyncMock(
            return_value=json.dumps(
                {"summary": "S", "tags": ["photography", "not-in-vocab"]}
            )
        ),
    ):
        result = await svc.enrich_place(place)
        assert result == ("S", ["photography"])
        payload = svc.repo.update.await_args.args[1]
        assert payload == {"summary": "S", "enriched_tags": ["photography"]}
        assert "tags" not in payload


@pytest.mark.asyncio
async def test_enrich_place_empty_filtered_tags_is_success() -> None:
    svc = PlaceService(AsyncMock())
    svc.repo.update = AsyncMock()
    place = SimpleNamespace(
        id=uuid.uuid4(), name="N", category="attraction", tags={}, summary=None
    )
    with patch(
        "src.places.service.chat_completion",
        new=AsyncMock(
            return_value=json.dumps(
                {"summary": "Generic place.", "tags": ["not-in-vocab"]}
            )
        ),
    ):
        result = await svc.enrich_place(place)
        assert result == ("Generic place.", [])
        assert svc.repo.update.await_count == 1
