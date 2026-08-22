"""OpenTripMap Places gateway — optional POI source behind places facade."""

from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.config import get_settings
from src.core.observability.logging import get_logger
from src.geo.schemas import RawPOI

logger = get_logger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)
_OTM_LIMIT = 200
_OTM_RATE = 1  # 1–3 cultural heritage scale; keep modest recall


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.is_server_error
    return False


def _category_from_kinds(kinds: str | None) -> str:
    k = (kinds or "").lower()
    if "cafe" in k or "coffee" in k:
        return "cafe"
    if "restaurant" in k or "foods" in k or "cuisine" in k:
        return "restaurant"
    if any(x in k for x in ("temple", "church", "mosque", "synagogue", "religion", "monastery")):
        return "temple" if "monastery" not in k else "monastery"
    if "museum" in k:
        return "museum"
    if "viewpoint" in k or "view_point" in k:
        return "viewpoint"
    if "park" in k:
        return "park"
    if any(x in k for x in ("peak", "waterfall", "natural", "mountain", "springs")):
        return "nature"
    if "historic" in k or "architecture" in k or "fortification" in k:
        return "historic"
    if "monastery" in k:
        return "monastery"
    return "attraction"


def _feature_to_poi(item: dict) -> RawPOI | None:
    xid = item.get("xid")
    name = item.get("name")
    if not xid or not name:
        return None
    point = item.get("point") or {}
    lat = point.get("lat")
    lon = point.get("lon")
    if lat is None or lon is None:
        return None
    kinds = item.get("kinds")
    rate = item.get("rate")
    raw_tags: dict = {"kinds": kinds, "otm_rate": rate, "source": "opentripmap"}
    return RawPOI(
        osm_id=f"otm:{xid}",
        name=str(name),
        lat=float(lat),
        lng=float(lon),
        category=_category_from_kinds(kinds if isinstance(kinds, str) else None),
        raw_tags=raw_tags,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=16),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def _get_radius(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    api_key: str,
    lat: float,
    lng: float,
    radius_m: int,
) -> list:
    url = f"{base_url.rstrip('/')}/places/radius"
    response = await client.get(
        url,
        params={
            "radius": radius_m,
            "lon": lng,
            "lat": lat,
            "rate": _OTM_RATE,
            "format": "json",
            "limit": _OTM_LIMIT,
            "apikey": api_key,
        },
    )
    if 400 <= response.status_code < 500:
        logger.warning("opentripmap_client_error", status_code=response.status_code)
        return []
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


async def fetch_opentripmap_pois(
    lat: float,
    lng: float,
    radius_km: float,
) -> list[RawPOI]:
    """Fetch OpenTripMap radius POIs. Empty key → []; network failure → []."""
    settings = get_settings()
    api_key = (settings.OPENTRIPMAP_API_KEY or "").strip()
    if not api_key:
        logger.warning("opentripmap_skipped_missing_key")
        return []

    radius_m = int(radius_km * 1000)
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            items = await _get_radius(
                client,
                base_url=settings.OPENTRIPMAP_BASE_URL,
                api_key=api_key,
                lat=lat,
                lng=lng,
                radius_m=radius_m,
            )
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning(
            "opentripmap_fetch_failed",
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            error=type(exc).__name__,
        )
        return []

    by_id: dict[str, RawPOI] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        poi = _feature_to_poi(item)
        if poi is not None:
            by_id[poi.osm_id] = poi
    return list(by_id.values())
