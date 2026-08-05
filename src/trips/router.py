"""Trips HTTP router — CRUD + GeoJSON + claim (P6.3)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.router import COOKIE_SESSION
from src.core.database.session import get_db
from src.core.pagination import PageParams, PaginatedResponse, paginate
from src.core.responses import ApiResponse
from src.core.security.jwt import TokenPayload
from src.core.security.permissions import optional_auth, require_auth
from src.trips.schemas import TripOut
from src.trips.service import TripService

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])


@router.get("")
async def list_trips(
    params: PageParams = Depends(),
    payload: TokenPayload = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[TripOut]:
    """Paginated trips for the authenticated user."""
    trips, total = await TripService(db).list_for_user(payload.user_id, params)
    return paginate([TripOut.from_trip(t) for t in trips], total, params)


@router.get("/{trip_id}")
async def get_trip(
    trip_id: uuid.UUID,
    request: Request,
    payload: TokenPayload | None = Depends(optional_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TripOut]:
    """Single trip — optional_auth + ownership (guest session or owner)."""
    session_id = request.cookies.get(COOKIE_SESSION)
    user_id = payload.user_id if payload else None
    trip = await TripService(db).get_for_access(
        trip_id, user_id=user_id, session_id=session_id
    )
    return ApiResponse(data=TripOut.from_trip(trip))


@router.get("/{trip_id}/geojson")
async def get_trip_geojson(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Public GeoJSON FeatureCollection for map renderers (geojson.io).
    Intentional envelope exception — not wrapped in ApiResponse.
    """
    svc = TripService(db)
    trip = await svc.get_trip_or_404(trip_id)
    return svc.build_geojson(trip)


@router.delete("/{trip_id}", status_code=204)
async def delete_trip(
    trip_id: uuid.UUID,
    request: Request,
    payload: TokenPayload = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    # DELETE requires full auth even though GET allows guest ownership —
    # intentional: no anonymous destructive actions.
    session_id = request.cookies.get(COOKIE_SESSION)
    await TripService(db).soft_delete_for_user(
        trip_id, payload.user_id, session_id=session_id
    )
    return Response(status_code=204)


@router.post("/{trip_id}/claim")
async def claim_trip(
    trip_id: uuid.UUID,
    request: Request,
    payload: TokenPayload = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TripOut]:
    """Claim an anonymous trip after login (session must match; unclaimed only)."""
    session_id = request.cookies.get(COOKIE_SESSION) or ""
    trip = await TripService(db).claim_trip(trip_id, payload.user_id, session_id)
    return ApiResponse(data=TripOut.from_trip(trip))
