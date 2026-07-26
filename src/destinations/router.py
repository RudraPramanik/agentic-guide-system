"""Destinations HTTP router — public catalog search and readiness."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_db
from src.core.responses import ApiResponse
from src.destinations.schemas import DestinationOut, DestinationReadinessOut
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
