"""P6.4 rate limiter factory — InMemory vs Redis selection + Redis fail-open."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.middleware.rate_limit import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    _reset_rate_limiter_for_tests,
    get_rate_limiter,
)


@pytest.fixture(autouse=True)
def _reset_limiter():
    _reset_rate_limiter_for_tests(None)
    yield
    _reset_rate_limiter_for_tests(None)


def test_empty_redis_url_selects_in_memory() -> None:
    limiter = get_rate_limiter()
    assert isinstance(limiter, InMemoryRateLimiter)


@pytest.mark.asyncio
async def test_redis_rate_limiter_sliding_window_allows_then_blocks() -> None:
    """Mock Redis pipeline: first call count=0 allow; second count=limit deny."""
    pipe1 = MagicMock()
    pipe1.zremrangebyscore = MagicMock()
    pipe1.zcard = MagicMock()
    pipe1.execute = AsyncMock(return_value=[0, 0])

    pipe2 = MagicMock()
    pipe2.zadd = MagicMock()
    pipe2.expire = MagicMock()
    pipe2.execute = AsyncMock(return_value=[1, True])

    pipe3 = MagicMock()
    pipe3.zremrangebyscore = MagicMock()
    pipe3.zcard = MagicMock()
    pipe3.execute = AsyncMock(return_value=[0, 2])  # already at limit 2

    client = MagicMock()
    client.pipeline = MagicMock(side_effect=[pipe1, pipe2, pipe3])

    limiter = RedisRateLimiter(client)
    allowed, remaining = await limiter.is_allowed("ip:/path", limit=2, window=60)
    assert allowed is True
    assert remaining == 1

    denied, rem = await limiter.is_allowed("ip:/path", limit=2, window=60)
    assert denied is False
    assert rem == 0


@pytest.mark.asyncio
async def test_redis_rate_limiter_raises_for_middleware_fail_open() -> None:
    """Redis errors propagate so middleware's fail-open catch can allow the request."""
    client = MagicMock()
    client.pipeline = MagicMock(side_effect=ConnectionError("redis down"))
    limiter = RedisRateLimiter(client)
    with pytest.raises(ConnectionError):
        await limiter.is_allowed("ip:/path", limit=10, window=60)
