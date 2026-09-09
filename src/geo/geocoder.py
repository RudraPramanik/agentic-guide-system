"""Nominatim geocoding gateway — all geocoding goes through this module."""

from __future__ import annotations

import asyncio
import math
import time

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import get_settings
from src.core.exceptions import ExternalServiceError
from src.core.observability.logging import get_logger
from src.geo.schemas import GeocodedPlace

logger = get_logger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
_rate_lock = asyncio.Lock()
_last_request_at: float = 0.0
_cache: dict[str, GeocodedPlace | None] = {}
_list_cache: dict[str, list[GeocodedPlace]] = {}
_cache_lock = asyncio.Lock()
_cache_hits: int = 0

# Policy / rate-limit responses — surface as 502 upstream, do not cache as miss.
_NOMINATIM_POLICY_STATUS = frozenset({403, 429})

# Admin / region types that are too large for a single prepare radius.
_OVERSIZED_ADDRESS_TYPES = frozenset(
    {
        "country",
        "state",
        "region",
        "province",
        "county",
        "state_district",
        "continent",
    }
)
_CITY_SCALE_TYPES = frozenset(
    {
        "city",
        "town",
        "village",
        "municipality",
        "suburb",
        "hamlet",
        "neighbourhood",
        "neighborhood",
        "quarter",
        "borough",
        "city_district",
    }
)
# Approx degrees: ~111 km per degree latitude; > ~120 km span ⇒ oversized.
_OVERSIZED_BBOX_DEG = 1.1


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
async def _fetch_nominatim(
    query: str,
    *,
    limit: int = 1,
    featuretype: str | None = None,
    viewbox: str | None = None,
    bounded: bool = False,
) -> list[dict] | None:
    """
    GET {NOMINATIM_BASE_URL}/search.
    On 403/429: raise ExternalServiceError (no retry, no cache).
    On other 4xx: log warning, return None (no retry).
    On success: parse JSON list.
    """
    settings = get_settings()
    params: dict[str, str | int] = {
        "q": query,
        "format": "json",
        "limit": max(1, min(limit, 20)),
        "addressdetails": 1,
    }
    if featuretype:
        params["featuretype"] = featuretype
    if viewbox:
        params["viewbox"] = viewbox
        if bounded:
            params["bounded"] = 1
    api_key = (settings.NOMINATIM_API_KEY or "").strip()
    if api_key:
        params["key"] = api_key

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        response = await client.get(
            f"{settings.NOMINATIM_BASE_URL.rstrip('/')}/search",
            params=params,
            headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
        )
        if response.status_code in _NOMINATIM_POLICY_STATUS:
            logger.warning(
                "nominatim_client_error",
                status_code=response.status_code,
                query=query,
            )
            raise ExternalServiceError(
                service="nominatim",
                message="Geocoding service rejected the request",
                details={"status_code": response.status_code, "query": query},
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


def _parse_bbox(raw: dict) -> tuple[float | None, float | None, float | None, float | None]:
    bb = raw.get("boundingbox")
    if not isinstance(bb, (list, tuple)) or len(bb) < 4:
        return None, None, None, None
    try:
        south, north, west, east = (float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3]))
    except (TypeError, ValueError):
        return None, None, None, None
    return south, north, west, east


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

    south, north, west, east = _parse_bbox(raw)
    osm_class = raw.get("class")
    osm_type_tag = raw.get("type")
    addresstype = raw.get("addresstype")

    return GeocodedPlace(
        name=name,
        lat=float(raw["lat"]),
        lng=float(raw["lon"]),
        osm_place_id=f"{raw['osm_type']}/{raw['osm_id']}",
        country=country,
        display_name=display_name,
        osm_class=str(osm_class) if osm_class else None,
        osm_type_tag=str(osm_type_tag) if osm_type_tag else None,
        addresstype=str(addresstype) if addresstype else None,
        bbox_south=south,
        bbox_north=north,
        bbox_west=west,
        bbox_east=east,
    )


def is_oversized(place: GeocodedPlace) -> bool:
    """True when geography is too large for a single prepare radius."""
    addr = (place.addresstype or "").lower()
    if addr in _OVERSIZED_ADDRESS_TYPES:
        return True
    osm_class = (place.osm_class or "").lower()
    osm_type = (place.osm_type_tag or "").lower()
    if osm_class == "boundary" and osm_type in {"administrative", "political"}:
        # City admin boundaries can be small — use bbox when present.
        if place.bbox_south is None:
            return addr in _OVERSIZED_ADDRESS_TYPES or addr == ""
    if (
        place.bbox_south is not None
        and place.bbox_north is not None
        and place.bbox_west is not None
        and place.bbox_east is not None
    ):
        lat_span = abs(place.bbox_north - place.bbox_south)
        lng_span = abs(place.bbox_east - place.bbox_west)
        # Crude km estimate at mid-latitude
        mid_lat = (place.bbox_north + place.bbox_south) / 2.0
        km_lat = lat_span * 111.0
        km_lng = lng_span * 111.0 * max(math.cos(math.radians(mid_lat)), 0.2)
        if max(km_lat, km_lng) > 120.0 or lat_span > _OVERSIZED_BBOX_DEG or lng_span > _OVERSIZED_BBOX_DEG:
            return True
    return False


def is_city_scale(place: GeocodedPlace) -> bool:
    """True when the hit looks like a plannable hub/city."""
    if is_oversized(place):
        return False
    addr = (place.addresstype or "").lower()
    osm_type = (place.osm_type_tag or "").lower()
    if addr in _CITY_SCALE_TYPES or osm_type in _CITY_SCALE_TYPES:
        return True
    # Small bbox without admin country/state tags → treat as local
    if (
        place.bbox_south is not None
        and place.bbox_north is not None
        and place.bbox_west is not None
        and place.bbox_east is not None
    ):
        lat_span = abs(place.bbox_north - place.bbox_south)
        lng_span = abs(place.bbox_east - place.bbox_west)
        return lat_span <= _OVERSIZED_BBOX_DEG and lng_span <= _OVERSIZED_BBOX_DEG
    return not is_oversized(place)


def viewbox_from_place(place: GeocodedPlace) -> str | None:
    """Nominatim viewbox string: left,top,right,bottom (west,north,east,south)."""
    if None in (place.bbox_west, place.bbox_north, place.bbox_east, place.bbox_south):
        return None
    return f"{place.bbox_west},{place.bbox_north},{place.bbox_east},{place.bbox_south}"


async def geocode(query: str) -> GeocodedPlace | None:
    """
    Public entry point. Manual cache — NOT lru_cache.

    Returns GeocodedPlace on success, None on soft miss/failure.
    Raises ExternalServiceError on Nominatim policy/rate rejection (403/429).
    Never raises httpx exceptions to callers.
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
        raw_results = await _fetch_nominatim(normalized, limit=1)
        if raw_results:
            result = _parse_result(raw_results[0])
    except ExternalServiceError:
        # Do not negative-cache policy failures — operator may fix UA/URL next request.
        raise
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


async def geocode_search(
    query: str,
    *,
    limit: int = 5,
    featuretype: str | None = None,
    viewbox: str | None = None,
    bounded: bool = False,
) -> list[GeocodedPlace]:
    """Multi-hit Nominatim search (separate cache from single-result geocode)."""
    global _cache_hits
    normalized = _normalize(query)
    cache_key = f"{normalized}|l={limit}|ft={featuretype or ''}|vb={viewbox or ''}|b={int(bounded)}"
    async with _cache_lock:
        if cache_key in _list_cache:
            _cache_hits += 1
            return list(_list_cache[cache_key])

    await _throttle()
    results: list[GeocodedPlace] = []
    try:
        raw_results = await _fetch_nominatim(
            normalized,
            limit=limit,
            featuretype=featuretype,
            viewbox=viewbox,
            bounded=bounded,
        )
        if raw_results:
            results = [_parse_result(r) for r in raw_results]
    except ExternalServiceError:
        raise
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning(
            "nominatim_geocode_search_failed",
            query=normalized,
            error=type(exc).__name__,
        )
        results = []

    async with _cache_lock:
        _list_cache[cache_key] = list(results)
    return results


def cache_stats() -> dict:
    """Test/debug helper: {"size": len(_cache), "hits": _cache_hits}."""
    return {"size": len(_cache) + len(_list_cache), "hits": _cache_hits}


def _clear_cache_for_tests() -> None:
    """Test-only reset — clears _cache and _cache_hits. Never called from app code."""
    global _cache_hits
    _cache.clear()
    _list_cache.clear()
    _cache_hits = 0
