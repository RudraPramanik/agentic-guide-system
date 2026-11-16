"""Fail closed on live providers for the legacy-contract snapshots."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.core.cache.backends import InMemoryCacheBackend, _reset_cache_backend_for_tests
from src.core.middleware.rate_limit import (
    InMemoryRateLimiter,
    _reset_rate_limiter_for_tests,
)


def _refuse(name: str):
    return AsyncMock(side_effect=AssertionError(f"{name} was called"))


@pytest.fixture(autouse=True)
def forbid_live_providers(monkeypatch):
    """No geocoder, LLM, or Qdrant. Cache and rate limit stay in-process."""
    geocode = _refuse("geocode")
    geocode_search = _refuse("geocode_search")
    chat_completion = _refuse("chat_completion")
    chat_with_tools = _refuse("chat_with_tools")

    monkeypatch.setattr("src.geo.geocoder.geocode", geocode)
    monkeypatch.setattr("src.geo.geocoder.geocode_search", geocode_search)
    monkeypatch.setattr("src.destinations.service.geocode", geocode)
    monkeypatch.setattr("src.destinations.service.geocode_search", geocode_search)
    monkeypatch.setattr("src.core.llm.client.chat_completion", chat_completion)
    monkeypatch.setattr("src.core.llm.client.chat_with_tools", chat_with_tools)
    monkeypatch.setattr("src.destinations.service.is_qdrant_available", lambda: False)
    monkeypatch.setattr("src.search.client.is_qdrant_available", lambda: False)

    _reset_cache_backend_for_tests(InMemoryCacheBackend())
    _reset_rate_limiter_for_tests(InMemoryRateLimiter())
    yield {
        "geocode": geocode,
        "geocode_search": geocode_search,
        "chat_completion": chat_completion,
        "chat_with_tools": chat_with_tools,
    }
    _reset_cache_backend_for_tests(None)
    _reset_rate_limiter_for_tests(None)
