"""Places HTTP router — list by destination and get by id."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import get_db
from src.core.pagination import PageParams, PaginatedResponse, paginate
from src.core.responses import ApiResponse
from src.places.schemas import PlaceOut
from src.places.service import PlaceService

router = APIRouter(prefix="/api/v1/places", tags=["places"])


@router.get("")
async def list_places(
    destination_id: uuid.UUID,
    params: PageParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[PlaceOut]:
    """Paginated places for a destination. Unknown destination → 404."""
    items, total = await PlaceService(db).list_by_destination(destination_id, params)
    return paginate(items, total, params)


@router.get("/{place_id}")
async def get_place(
    place_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PlaceOut]:
    """Single place by id. Unknown place → 404."""
    return ApiResponse(data=await PlaceService(db).get_by_id(place_id))
