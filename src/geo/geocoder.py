"""Nominatim geocoding gateway — all geocoding goes through this module."""

from __future__ import annotations

import asyncio
import time

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import get_settings
from src.core.observability.logging import get_logger
from src.geo.schemas import GeocodedPlace

logger = get_logger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
_rate_lock = asyncio.Lock()
_last_request_at: float = 0.0
_cache: dict[str, GeocodedPlace | None] = {}
_cache_lock = asyncio.Lock()
_cache_hits: int = 0


def _normalize(query: str) -> str:
    """Strip, collapse internal whitespace, lowercase — used as the cache key."""
    return " ".join(query.strip().lower().split())


async def _throttle() -> None:
    """Enforce Nominatim's 1 req/sec policy between outbound calls (this process)."""
    global _last_request_at
    async with _rate_lock:
        now = time.monotonic()
        elapsed = now - _last_request_at
        if _last_request_at > 0.0 and elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        _last_request_at = time.monotonic()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def _fetch_nominatim(query: str) -> list[dict] | None:
    """
    GET {NOMINATIM_BASE_URL}/search.
    On 4xx: log warning, return None (no retry).
    On success: parse JSON list.
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        response = await client.get(
            f"{settings.NOMINATIM_BASE_URL.rstrip('/')}/search",
            params={
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            },
            headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
        )
        if 400 <= response.status_code < 500:
            logger.warning(
                "nominatim_client_error",
                status_code=response.status_code,
                query=query,
            )
            return None
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            return None
        return data


def _parse_result(raw: dict) -> GeocodedPlace:
    """Map a Nominatim search hit to GeocodedPlace."""
    display_name = str(raw.get("display_name") or "")
    name = str(raw.get("name") or "").strip()
    if not name:
        name = display_name.split(",")[0].strip() if display_name else "Unknown"

    address = raw.get("address") or {}
    country_code = address.get("country_code")
    if country_code:
        country = str(country_code).upper()
    elif address.get("country"):
        country = str(address["country"])
    else:
        country = "Unknown"

    return GeocodedPlace(
        name=name,
        lat=float(raw["lat"]),
        lng=float(raw["lon"]),
        osm_place_id=f"{raw['osm_type']}/{raw['osm_id']}",
        country=country,
        display_name=display_name,
    )


async def geocode(query: str) -> GeocodedPlace | None:
    """
    Public entry point. Manual cache — NOT lru_cache.

    Returns GeocodedPlace on success, None on failure (never raises httpx to callers).
    """
    global _cache_hits

    normalized = _normalize(query)
    async with _cache_lock:
        if normalized in _cache:
            _cache_hits += 1
            return _cache[normalized]

    await _throttle()

    result: GeocodedPlace | None = None
    try:
        raw_results = await _fetch_nominatim(normalized)
        if raw_results:
            result = _parse_result(raw_results[0])
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning(
            "nominatim_geocode_failed",
            query=normalized,
            error=type(exc).__name__,
        )
        result = None

    async with _cache_lock:
        _cache[normalized] = result

    return result


def cache_stats() -> dict:
    """Test/debug helper: {"size": len(_cache), "hits": _cache_hits}."""
    return {"size": len(_cache), "hits": _cache_hits}


def _clear_cache_for_tests() -> None:
    """Test-only reset — clears _cache and _cache_hits. Never called from app code."""
    global _cache_hits
    _cache.clear()
    _cache_hits = 0
