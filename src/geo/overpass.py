"""Overpass API gateway — all POI scraping goes through this module."""

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

# read=90: step/blueprint cited read=30, which aborts before OverpassQL [timeout:60]
# and before real Darjeeling-sized responses on public mirrors (see design D3).
_HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)

_OVERPASS_QL_TEMPLATE = """[out:json][timeout:60];
(
  node["tourism"~"attraction|viewpoint|museum|monastery"](around:{radius_m},{lat},{lng});
  way["tourism"~"attraction|viewpoint|museum|monastery"](around:{radius_m},{lat},{lng});
  node["leisure"="park"](around:{radius_m},{lat},{lng});
  node["highway"="trailhead"](around:{radius_m},{lat},{lng});
  node["amenity"~"cafe|restaurant"](around:{radius_m},{lat},{lng});
  node["amenity"="place_of_worship"](around:{radius_m},{lat},{lng});
  node["historic"](around:{radius_m},{lat},{lng});
  way["historic"](around:{radius_m},{lat},{lng});
  node["natural"~"peak|waterfall"](around:{radius_m},{lat},{lng});
);
out center tags;"""


def _is_retryable(exc: BaseException) -> bool:
    """Retry timeouts, connect failures, and transient Overpass 5xx (e.g. 504)."""
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.is_server_error
    return False


def _category_from_tags(tags: dict) -> str:
    """Priority-ordered mapping: tourism → amenity → leisure/highway → historic/natural."""
    tourism = tags.get("tourism")
    if tourism == "museum":
        return "museum"
    if tourism == "viewpoint":
        return "viewpoint"
    if tourism == "monastery":
        return "monastery"
    if tourism == "attraction":
        return "attraction"
    amenity = tags.get("amenity")
    if amenity == "cafe":
        return "cafe"
    if amenity == "restaurant":
        return "restaurant"
    if amenity == "place_of_worship":
        return "temple"
    if tags.get("leisure") == "park":
        return "park"
    if tags.get("highway") == "trailhead":
        return "trailhead"
    if tags.get("historic"):
        return "historic"
    natural = tags.get("natural")
    if natural in ("peak", "waterfall"):
        return "nature"
    return "attraction"


def _element_to_poi(element: dict) -> RawPOI | None:
    """
    Map an Overpass element to RawPOI.
    Skip unnamed elements and those without usable coordinates.
    """
    tags = element.get("tags") or {}
    name = tags.get("name")
    if not name:
        return None

    lat = element.get("lat")
    lon = element.get("lon")
    if lat is None or lon is None:
        center = element.get("center") or {}
        lat = center.get("lat")
        lon = center.get("lon")
    if lat is None or lon is None:
        return None

    return RawPOI(
        osm_id=f"{element['type']}/{element['id']}",
        name=str(name),
        lat=float(lat),
        lng=float(lon),
        category=_category_from_tags(tags),
        raw_tags=dict(tags),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=16),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def _post_overpass(query: str) -> dict:
    """POST to settings.OVERPASS_API_URL with form data. 4xx -> log + return {"elements": []}."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        response = await client.post(
            settings.OVERPASS_API_URL,
            data={"data": query},
            headers={
                "User-Agent": settings.NOMINATIM_USER_AGENT,
                "Accept": "application/json",
            },
        )
        if 400 <= response.status_code < 500:
            logger.warning(
                "overpass_client_error",
                status_code=response.status_code,
            )
            return {"elements": []}
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            return {"elements": []}
        return data


def _build_overpass_query(lat: float, lng: float, radius_km: float) -> str:
    radius_m = int(radius_km * 1000)
    return _OVERPASS_QL_TEMPLATE.format(radius_m=radius_m, lat=lat, lng=lng)


async def fetch_pois(lat: float, lng: float, radius_km: float) -> list[RawPOI]:
    """
    Public entry point.
    1. Build OverpassQL
    2. POST via _post_overpass
    3. Parse elements -> RawPOI, skip unnamed
    4. Deduplicate by osm_id (last wins)
    5. Return list (may be empty)
    """
    query = _build_overpass_query(lat, lng, radius_km)
    try:
        payload = await _post_overpass(query)
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning(
            "overpass_fetch_failed",
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            error=type(exc).__name__,
        )
        return []

    elements = payload.get("elements") or []
    by_osm_id: dict[str, RawPOI] = {}
    for element in elements:
        if not isinstance(element, dict):
            continue
        poi = _element_to_poi(element)
        if poi is not None:
            by_osm_id[poi.osm_id] = poi
    return list(by_osm_id.values())
