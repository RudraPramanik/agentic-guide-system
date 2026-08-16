"""P6.4 CacheBackend — in-memory TTL + Redis error fail-soft."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.cache.backends import (
    InMemoryCacheBackend,
    RedisCacheBackend,
    _reset_cache_backend_for_tests,
    get_cache_backend,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    _reset_cache_backend_for_tests(None)
    yield
    _reset_cache_backend_for_tests(None)


@pytest.mark.asyncio
async def test_empty_redis_url_selects_in_memory() -> None:
    backend = get_cache_backend()
    assert isinstance(backend, InMemoryCacheBackend)


@pytest.mark.asyncio
async def test_in_memory_hit_miss_and_ttl() -> None:
    cache = InMemoryCacheBackend()
    assert await cache.get("k") is None
    await cache.set("k", "v", ttl_seconds=60)
    assert await cache.get("k") == "v"

    # Expired entry
    cache._store["expired"] = ("old", 0.0)  # already past monotonic
    assert await cache.get("expired") is None

    await cache.set("gone", "x", ttl_seconds=60)
    await cache.delete("gone")
    assert await cache.get("gone") is None


@pytest.mark.asyncio
async def test_redis_cache_get_error_is_miss() -> None:
    client = MagicMock()
    client.get = AsyncMock(side_effect=RuntimeError("redis down"))
    backend = RedisCacheBackend(client)
    assert await backend.get("any") is None


@pytest.mark.asyncio
async def test_redis_cache_set_error_is_noop() -> None:
    client = MagicMock()
    client.set = AsyncMock(side_effect=RuntimeError("redis down"))
    backend = RedisCacheBackend(client)
    await backend.set("k", "v", ttl_seconds=10)  # must not raise


@pytest.mark.asyncio
async def test_redis_cache_delete_error_is_noop() -> None:
    client = MagicMock()
    client.delete = AsyncMock(side_effect=RuntimeError("redis down"))
    backend = RedisCacheBackend(client)
    await backend.delete("k")  # must not raise
