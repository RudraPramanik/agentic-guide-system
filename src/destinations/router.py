"""Destinations HTTP router — public catalog search, readiness, and prepare."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_db
from src.core.responses import ApiResponse
from src.destinations.dependencies import rate_limit_destinations_prepare
from src.destinations.schemas import (
    DestinationOut,
    DestinationPrepareOut,
    DestinationReadinessOut,
    PrepareIn,
)
from src.destinations.service import DestinationService

router = APIRouter(prefix="/api/v1/destinations", tags=["destinations"])


@router.get("/search")
async def search_destinations(
    q: str = Query(min_length=2, max_length=200),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[DestinationOut]]:
    """DB-first search with Nominatim cache-aside fallback."""
    results = await DestinationService(db).search(q)
    return ApiResponse(data=[DestinationOut.model_validate(d) for d in results])


@router.get("/{destination_id}/readiness")
async def get_destination_readiness(
    destination_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[DestinationReadinessOut]:
    """Readiness score for a destination (pure compute_readiness via service)."""
    return ApiResponse(data=await DestinationService(db).get_readiness(destination_id))


@router.post("/{destination_id}/prepare")
async def prepare_destination(
    destination_id: uuid.UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_destinations_prepare),
    body: PrepareIn | None = None,
) -> ApiResponse[DestinationPrepareOut]:
    """Public Overpass seed kickoff. 200 if already at floor; 202 if scrape started."""
    payload = body or PrepareIn()
    result = await DestinationService(db).prepare(
        destination_id,
        radius_km=payload.radius_km,
    )
    response.status_code = 200 if result.status == "ready" else 202
    return ApiResponse(data=result)
