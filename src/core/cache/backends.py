"""Swappable cache backends — InMemory (dev) / Redis (prod when REDIS_URL set)."""

from __future__ import annotations

import time
from typing import Protocol

import structlog

from src.config import get_settings

log = structlog.get_logger()

_CACHE_KEY_PREFIX = "wandr:cache:"


class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...

    async def delete(self, key: str) -> None: ...


class InMemoryCacheBackend:
    """Process-local TTL cache. Not shared across workers."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}

    async def get(self, key: str) -> str | None:
        try:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at <= time.monotonic():
                del self._store[key]
                return None
            return value
        except Exception as exc:
            log.warning("cache.get_error", backend="memory", error=str(exc))
            return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            ttl = max(int(ttl_seconds), 0)
            expires_at = time.monotonic() + ttl
            self._store[key] = (value, expires_at)
            # Opportunistic eviction of expired keys
            now = time.monotonic()
            stale = [k for k, (_, exp) in self._store.items() if exp <= now]
            for k in stale:
                del self._store[k]
        except Exception as exc:
            log.warning("cache.set_error", backend="memory", error=str(exc))

    async def delete(self, key: str) -> None:
        try:
            self._store.pop(key, None)
        except Exception as exc:
            log.warning("cache.delete_error", backend="memory", error=str(exc))


class RedisCacheBackend:
    """Redis string GET/SET with TTL. Errors → miss / no-op (never raise to callers)."""

    def __init__(self, client: object) -> None:
        self._client = client

    async def get(self, key: str) -> str | None:
        try:
            value = await self._client.get(f"{_CACHE_KEY_PREFIX}{key}")  # type: ignore[attr-defined]
            if value is None:
                return None
            if isinstance(value, bytes):
                return value.decode("utf-8")
            return str(value)
        except Exception as exc:
            log.warning("cache.get_error", backend="redis", error=str(exc))
            return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            ttl = max(int(ttl_seconds), 1)
            await self._client.set(  # type: ignore[attr-defined]
                f"{_CACHE_KEY_PREFIX}{key}",
                value,
                ex=ttl,
            )
        except Exception as exc:
            log.warning("cache.set_error", backend="redis", error=str(exc))

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(f"{_CACHE_KEY_PREFIX}{key}")  # type: ignore[attr-defined]
        except Exception as exc:
            log.warning("cache.delete_error", backend="redis", error=str(exc))


_cache_backend: CacheBackend | None = None


def _build_redis_client():
    from redis.asyncio import Redis

    settings = get_settings()
    return Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
        decode_responses=True,
    )


def get_cache_backend() -> CacheBackend:
    """Return process-wide cache backend (InMemory if REDIS_URL empty)."""
    global _cache_backend
    if _cache_backend is not None:
        return _cache_backend

    settings = get_settings()
    if settings.REDIS_URL:
        _cache_backend = RedisCacheBackend(_build_redis_client())
    else:
        _cache_backend = InMemoryCacheBackend()
    return _cache_backend


def _reset_cache_backend_for_tests(backend: CacheBackend | None = None) -> None:
    """Test helper — force a backend or clear so next get_cache_backend() rebuilds."""
    global _cache_backend
    _cache_backend = backend
