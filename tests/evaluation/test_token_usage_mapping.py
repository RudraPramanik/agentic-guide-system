"""EvaluationService maps token_usage from TravelState."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.evaluation.service import EvaluationService


@pytest.mark.asyncio
async def test_record_generation_maps_token_usage() -> None:
    session = MagicMock()
    service = EvaluationService(session)
    created = MagicMock()
    service.repo.create_generation = AsyncMock(return_value=created)

    dest = uuid.uuid4()
    await service.record_generation(
        {
            "destination_id": str(dest),
            "raw_input": "3 days",
            "token_usage": {
                "prompt_tokens": 11,
                "completion_tokens": 22,
                "total_tokens": 33,
            },
            "llm_retry_count": 2,
            "tool_trace": [],
        }
    )
    data = service.repo.create_generation.await_args.args[0]
    assert data["token_usage"]["total_tokens"] == 33
    assert data["llm_retry_count"] == 2


@pytest.mark.asyncio
async def test_record_generation_empty_token_usage() -> None:
    session = MagicMock()
    service = EvaluationService(session)
    service.repo.create_generation = AsyncMock(return_value=MagicMock())

    await service.record_generation(
        {
            "destination_id": str(uuid.uuid4()),
            "raw_input": "x",
        }
    )
    data = service.repo.create_generation.await_args.args[0]
    assert data["token_usage"] == {}
    assert data["llm_retry_count"] == 0
