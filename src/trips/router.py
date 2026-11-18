"""Trips HTTP router — CRUD + GeoJSON + claim (P6.3) + day-edit (P7.3)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.router import COOKIE_SESSION
from src.config import get_settings
from src.core.database.session import get_db
from src.core.pagination import PageParams, PaginatedResponse, paginate
from src.core.responses import ApiResponse
from src.core.security.jwt import TokenPayload
from src.core.security.permissions import optional_auth, require_auth
from src.trips.dependencies import rate_limit_trip_edit
from src.trips.exceptions import TripEditValidationError
from src.trips.schemas import AddStopIn, ReorderStopsIn, TripOut
from src.trips.service import TripService

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])


def _parse_if_match(header: str | None) -> int | None:
    if header is None or not str(header).strip():
        return None
    token = str(header).strip()
    if token.startswith("W/"):
        token = token[2:].strip()
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        token = token[1:-1]
    try:
        return int(token)
    except ValueError as exc:
        raise TripEditValidationError(
            "If-Match must be an integer trip version",
            code="invalid_if_match",
        ) from exc


def _expected_version(if_match: str | None, body_version: int | None) -> int | None:
    if not get_settings().CANONICAL_TRIP_V2_ENABLED:
        return None
    header = _parse_if_match(if_match)
    if header is not None and body_version is not None and header != body_version:
        raise TripEditValidationError(
            "If-Match and expected_version disagree",
            code="version_header_mismatch",
        )
    return header if header is not None else body_version


def _set_etag(response: Response, trip: object) -> None:
    if not get_settings().CANONICAL_TRIP_V2_ENABLED:
        return
    version = getattr(trip, "version", None)
    if version is None:
        return
    response.headers["ETag"] = f'"{int(version)}"'


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
    response: Response,
    payload: TokenPayload | None = Depends(optional_auth),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TripOut]:
    """Single trip — optional_auth + ownership (guest session or owner)."""
    session_id = request.cookies.get(COOKIE_SESSION)
    user_id = payload.user_id if payload else None
    trip = await TripService(db).get_for_access(
        trip_id, user_id=user_id, session_id=session_id
    )
    _set_etag(response, trip)
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


@router.patch("/{trip_id}/days/{day}/stops/reorder")
async def reorder_day_stops(
    trip_id: uuid.UUID,
    day: int,
    body: ReorderStopsIn,
    response: Response,
    payload: TokenPayload = Depends(rate_limit_trip_edit),
    db: AsyncSession = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> ApiResponse[TripOut]:
    trip = await TripService(db).reorder_stops(
        trip_id,
        day,
        body.place_ids,
        payload.user_id,
        expected_version=_expected_version(if_match, body.expected_version),
    )
    _set_etag(response, trip)
    return ApiResponse(data=TripOut.from_trip(trip))


@router.delete("/{trip_id}/days/{day}/stops/{place_id}")
async def remove_day_stop(
    trip_id: uuid.UUID,
    day: int,
    place_id: uuid.UUID,
    response: Response,
    payload: TokenPayload = Depends(rate_limit_trip_edit),
    db: AsyncSession = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> ApiResponse[TripOut]:
    trip = await TripService(db).remove_stop(
        trip_id,
        day,
        place_id,
        payload.user_id,
        expected_version=_expected_version(if_match, None),
    )
    _set_etag(response, trip)
    return ApiResponse(data=TripOut.from_trip(trip))


@router.post("/{trip_id}/days/{day}/stops")
async def add_day_stop(
    trip_id: uuid.UUID,
    day: int,
    body: AddStopIn,
    response: Response,
    payload: TokenPayload = Depends(rate_limit_trip_edit),
    db: AsyncSession = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> ApiResponse[TripOut]:
    trip = await TripService(db).add_stop(
        trip_id,
        day,
        body.place_id,
        payload.user_id,
        expected_version=_expected_version(if_match, body.expected_version),
    )
    _set_etag(response, trip)
    return ApiResponse(data=TripOut.from_trip(trip))


@router.post("/{trip_id}/days/{day}/reoptimize")
async def reoptimize_day(
    trip_id: uuid.UUID,
    day: int,
    response: Response,
    payload: TokenPayload = Depends(rate_limit_trip_edit),
    db: AsyncSession = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> ApiResponse[TripOut]:
    trip = await TripService(db).reoptimize_day(
        trip_id,
        day,
        payload.user_id,
        expected_version=_expected_version(if_match, None),
    )
    _set_etag(response, trip)
    return ApiResponse(data=TripOut.from_trip(trip))
