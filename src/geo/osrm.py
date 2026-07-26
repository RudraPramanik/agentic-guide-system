"""OSRM routing gateway — all driving-route HTTP goes through this module."""

from __future__ import annotations

import math

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from src.config import get_settings
from src.core.observability.logging import get_logger
from src.geo.schemas import RouteResult

logger = get_logger(__name__)

_HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
_HAVERSINE_ROAD_FACTOR = 1.4
_AVG_SPEED_KMH = 30.0


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two WGS84 points in kilometers."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _fallback_route(waypoints: list[tuple[float, float]]) -> RouteResult:
    """Sum haversine legs x 1.4; duration from AVG_SPEED; always fallback_used=True."""
    distance_km = 0.0
    for i in range(len(waypoints) - 1):
        lat1, lng1 = waypoints[i]
        lat2, lng2 = waypoints[i + 1]
        distance_km += _haversine_km(lat1, lng1, lat2, lng2)
    distance_km *= _HAVERSINE_ROAD_FACTOR
    duration_min = (distance_km / _AVG_SPEED_KMH) * 60.0
    logger.warning(
        "osrm.fallback",
        distance_km=round(distance_km, 3),
        duration_min=round(duration_min, 3),
        legs=len(waypoints) - 1,
    )
    return RouteResult(
        distance_km=distance_km,
        duration_min=duration_min,
        encoded_polyline=None,
        fallback_used=True,
    )


@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(1),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
async def _call_osrm(waypoints: list[tuple[float, float]]) -> dict | None:
    """GET OSRM driving route. Waypoints are (lat, lng); URL uses lng,lat."""
    settings = get_settings()
    coords = ";".join(f"{lng},{lat}" for lat, lng in waypoints)
    url = (
        f"{settings.OSRM_BASE_URL.rstrip('/')}/route/v1/driving/{coords}"
        f"?overview=full&geometries=polyline"
    )
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        response = await client.get(url)
        if response.is_client_error:
            logger.warning(
                "osrm.client_error",
                status_code=response.status_code,
                url=url,
            )
            return None
        response.raise_for_status()
        return response.json()


async def get_route(waypoints: list[tuple[float, float]]) -> RouteResult:
    """Public entry: OSRM route or haversine fallback. Never raises httpx to callers."""
    if len(waypoints) < 2:
        raise ValueError("get_route requires at least 2 waypoints")

    try:
        payload = await _call_osrm(waypoints)
    except Exception as exc:  # noqa: BLE001 — named fallback; never fail the caller
        logger.warning("osrm.call_failed", error=str(exc))
        return _fallback_route(waypoints)

    if not payload:
        return _fallback_route(waypoints)

    routes = payload.get("routes") or []
    if not routes:
        return _fallback_route(waypoints)

    route = routes[0]
    distance_m = route.get("distance")
    duration_s = route.get("duration")
    if distance_m is None or duration_s is None:
        return _fallback_route(waypoints)

    return RouteResult(
        distance_km=float(distance_m) / 1000.0,
        duration_min=float(duration_s) / 60.0,
        encoded_polyline=route.get("geometry"),
        fallback_used=False,
    )
