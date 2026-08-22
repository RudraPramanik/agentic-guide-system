"""Geoapify Places gateway — optional POI source behind places facade."""

from __future__ import annotations

import hashlib

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
_GEOAPIFY_LIMIT = 100
# Tourism + food + worship + nature — keep request count low (1 credit / 20 places).
_GEOAPIFY_CATEGORIES = ",".join(
    [
        "catering.cafe",
        "catering.restaurant",
        "tourism.attraction",
        "tourism.sights",
        "entertainment.museum",
        "religion",
        "natural",
        "heritage",
        "leisure.park",
    ]
)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.is_server_error
    return False


def _category_from_geoapify(props: dict) -> str:
    cats = props.get("categories") or []
    if isinstance(cats, str):
        cats = [cats]
    joined = " ".join(str(c) for c in cats).lower()
    if "catering.cafe" in joined or joined.endswith(".cafe"):
        return "cafe"
    if "catering.restaurant" in joined or "restaurant" in joined:
        return "restaurant"
    if "religion" in joined or "place_of_worship" in joined:
        return "temple"
    if "museum" in joined:
        return "museum"
    if "viewpoint" in joined:
        return "viewpoint"
    if "leisure.park" in joined or "park" in joined:
        return "park"
    if "natural" in joined:
        return "nature"
    if "heritage" in joined or "historic" in joined:
        return "historic"
    return "attraction"


def _feature_to_poi(feature: dict) -> RawPOI | None:
    props = feature.get("properties") or {}
    place_id = props.get("place_id")
    name = props.get("name")
    if not name:
        return None
    if place_id is not None:
        # place_id strings often exceed places.osm_id VARCHAR(64) — hash to fit.
        raw = str(place_id)
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
        osm_id = f"geoapify:{digest}"  # 9 + 40 = 49 chars
    else:
        ds = props.get("datasource") or {}
        raw_ds = ds.get("raw") or {}
        osm_type = raw_ds.get("osm_type")
        osm_id_num = raw_ds.get("osm_id")
        if osm_type and osm_id_num is not None:
            osm_id = f"geoapify:{osm_type}/{osm_id_num}"
            if len(osm_id) > 64:
                digest = hashlib.sha1(osm_id.encode("utf-8")).hexdigest()
                osm_id = f"geoapify:{digest}"
        else:
            return None

    lat = props.get("lat")
    lon = props.get("lon")
    if lat is None or lon is None:
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if len(coords) >= 2:
            lon, lat = coords[0], coords[1]
    if lat is None or lon is None:
        return None

    return RawPOI(
        osm_id=str(osm_id),
        name=str(name),
        lat=float(lat),
        lng=float(lon),
        category=_category_from_geoapify(props),
        raw_tags={
            "categories": props.get("categories"),
            "source": "geoapify",
            "formatted": props.get("formatted"),
            "geoapify_place_id": props.get("place_id"),
        },
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=16),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def _get_places(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    api_key: str,
    lat: float,
    lng: float,
    radius_m: int,
) -> list:
    url = f"{base_url.rstrip('/')}/places"
    response = await client.get(
        url,
        params={
            "categories": _GEOAPIFY_CATEGORIES,
            "filter": f"circle:{lng},{lat},{radius_m}",
            "bias": f"proximity:{lng},{lat}",
            "limit": _GEOAPIFY_LIMIT,
            "apiKey": api_key,
        },
    )
    if 400 <= response.status_code < 500:
        logger.warning("geoapify_client_error", status_code=response.status_code)
        return []
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        return []
    features = data.get("features") or []
    return features if isinstance(features, list) else []


async def fetch_geoapify_pois(
    lat: float,
    lng: float,
    radius_km: float,
) -> list[RawPOI]:
    """Fetch Geoapify Places. Empty key → []; network failure → []."""
    settings = get_settings()
    api_key = (settings.GEOAPIFY_API_KEY or "").strip()
    if not api_key:
        logger.warning("geoapify_skipped_missing_key")
        return []

    radius_m = int(radius_km * 1000)
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            features = await _get_places(
                client,
                base_url=settings.GEOAPIFY_BASE_URL,
                api_key=api_key,
                lat=lat,
                lng=lng,
                radius_m=radius_m,
            )
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning(
            "geoapify_fetch_failed",
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            error=type(exc).__name__,
        )
        return []

    by_id: dict[str, RawPOI] = {}
    for feature in features:
        if not isinstance(feature, dict):
            continue
        poi = _feature_to_poi(feature)
        if poi is not None:
            by_id[poi.osm_id] = poi
    return list(by_id.values())
