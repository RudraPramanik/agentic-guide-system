"""Additive location HTTP routes — dark when LOCATION_V2_ENABLED is false."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.database.session import get_db
from src.core.exceptions import NotFoundError
from src.core.responses import ApiResponse
from src.location_intelligence.exceptions import (
    InvalidCoordinatesError,
    LocationIntelligenceError,
    as_http_error,
)
from src.location_intelligence.map_pin import map_pin_location
from src.location_intelligence.schemas import (
    LocationResolution,
    LocationType,
    ResolvedLocation,
    SearchArea,
)
from src.location_intelligence.service import LocationIntelligenceService

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


class LocationQueryIn(BaseModel):
    query: str = Field(min_length=2, max_length=200)


class LocationResolveIn(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    provider: Literal["nominatim", "catalog", "user"] | None = None
    provider_id: str | None = None


class LocationSearchAreaIn(BaseModel):
    anchor: ResolvedLocation
    radius_km: float | None = None
    polygon_geojson: dict[str, Any] | None = None


def _require_flag() -> None:
    if not get_settings().LOCATION_V2_ENABLED:
        raise NotFoundError(message="Location V2 is not enabled")


@router.post("/search")
async def locations_search(
    body: LocationQueryIn,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LocationResolution]:
    _require_flag()
    result = await LocationIntelligenceService(session=db).search(body.query)
    return ApiResponse(data=result)


@router.post("/resolve")
async def locations_resolve(
    body: LocationResolveIn,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LocationResolution]:
    _require_flag()
    svc = LocationIntelligenceService(session=db)
    resolution = await svc.search(body.query)
    if body.provider is None or body.provider_id is None:
        return ApiResponse(data=resolution)

    selected: ResolvedLocation | None = None
    for candidate in resolution.candidates:
        if (
            candidate.provider == body.provider
            and candidate.provider_id == body.provider_id
        ):
            selected = candidate
            break
    if selected is None:
        return ApiResponse(
            data=LocationResolution(
                status="not_found",
                selected=None,
                candidates=[],
                requires_confirmation=False,
                reason="anchor_not_confirmed",
            )
        )
    return ApiResponse(
        data=LocationResolution(
            status="resolved",
            selected=selected,
            candidates=resolution.candidates,
            requires_confirmation=False,
            reason=None,
        )
    )


@router.post("/search-area")
async def locations_search_area(
    body: LocationSearchAreaIn,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SearchArea]:
    _require_flag()
    svc = LocationIntelligenceService(session=db)
    try:
        anchor = body.anchor
        if anchor.provider == "user" or anchor.location_type == LocationType.MAP_PIN:
            # Re-validate coordinates through the map-pin builder.
            anchor = map_pin_location(
                anchor.lat,
                anchor.lng,
                canonical_name=anchor.canonical_name,
            )
        else:
            if not (-90.0 <= anchor.lat <= 90.0) or not (-180.0 <= anchor.lng <= 180.0):
                raise InvalidCoordinatesError()
        area = svc.search_area_for(
            anchor,
            user_radius_km=body.radius_km,
            polygon_geojson=body.polygon_geojson,
        )
    except LocationIntelligenceError as exc:
        raise as_http_error(exc) from exc
    return ApiResponse(data=area)
