"""search_places — DISCOVER; Qdrant first, PostGIS radius fallback."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.core.database.session import AsyncSessionLocal
from src.places.models import Place
from src.places.repository import PlaceRepository
from src.planner.tools._helpers import (
    as_uuid,
    candidate_to_dict,
    place_to_candidate,
    search_query_from_state,
    state_get,
)
from src.planner.tools.constants import SEARCH_DEFAULT_RADIUS_KM, SEARCH_DEFAULT_TOP_K
from src.planner.tools.schemas import SearchPlacesIn, ToolResult
from src.search import places_index


def _ctx_dest(ctx: Any, state: Any) -> UUID | None:
    raw = getattr(ctx, "destination_id", None) if ctx is not None else None
    if raw is None:
        raw = state_get(state, "destination_id")
    return as_uuid(raw) if raw is not None else None


def _base_coords(ctx: Any, state: Any) -> tuple[float | None, float | None]:
    lat = getattr(ctx, "base_lat", None) if ctx is not None else None
    lng = getattr(ctx, "base_lng", None) if ctx is not None else None
    if lat is None:
        lat = state_get(state, "base_lat")
    if lng is None:
        lng = state_get(state, "base_lng")
    return lat, lng


async def _load_places_by_ids(session: Any, ids: list[UUID]) -> list[Place]:
    if not ids:
        return []
    stmt = select(Place).where(Place.id.in_(ids), Place.deleted_at.is_(None))
    result = await session.execute(stmt)
    by_id = {p.id: p for p in result.scalars().all()}
    return [by_id[i] for i in ids if i in by_id]


async def run(
    inp: SearchPlacesIn,
    ctx: Any = None,
    state: Any = None,
) -> ToolResult:
    dest_id = _ctx_dest(ctx, state)
    if dest_id is None:
        return ToolResult(
            ok=False,
            code="precondition_failed",
            message="destination_id required",
        )

    top_k = inp.top_k
    if top_k is None:
        top_k = state_get(state, "search_top_k") or SEARCH_DEFAULT_TOP_K
    top_k = max(int(top_k), SEARCH_DEFAULT_TOP_K)
    query = search_query_from_state(state, inp.query)

    own_session = False
    session = getattr(ctx, "db", None) if ctx is not None else None
    if session is None:
        session = AsyncSessionLocal()
        own_session = True

    used_geo_fallback = False
    candidates: list[dict] = []
    fusion_diagnostics: dict | None = None

    try:
        outcome = await places_index.search_places_with_diagnostics(
            query, dest_id, top_k=top_k
        )
        hits = outcome.hits
        fusion_diagnostics = outcome.diagnostics
        place_ids: list[UUID] = []
        for h in hits:
            try:
                place_ids.append(UUID(str(h.place_id)))
            except ValueError:
                continue

        places = await _load_places_by_ids(session, place_ids) if place_ids else []

        if not places:
            used_geo_fallback = True
            lat, lng = _base_coords(ctx, state)
            if lat is None or lng is None:
                data: dict = {
                    "candidate_pois": [],
                    "used_geo_fallback": True,
                    "search_top_k": top_k,
                }
                if fusion_diagnostics is not None:
                    data["fusion_diagnostics"] = fusion_diagnostics
                return ToolResult(
                    ok=True,
                    code="empty_candidates",
                    message="no search hits and missing base coordinates for fallback",
                    data=data,
                    fallback_used=True,
                )
            repo = PlaceRepository(session)
            places = await repo.find_within_radius(
                float(lat),
                float(lng),
                SEARCH_DEFAULT_RADIUS_KM,
                limit=top_k,
            )
            # Prefer destination-scoped results when available
            places = [p for p in places if p.destination_id == dest_id] or places

        candidates = [candidate_to_dict(place_to_candidate(p)) for p in places]
        code = None
        message = None
        if not candidates:
            code = "empty_candidates"
            message = "no places found via search or geo fallback"

        data = {
            "candidate_pois": candidates,
            "used_geo_fallback": used_geo_fallback,
            "search_top_k": top_k,
            "query": query,
        }
        if fusion_diagnostics is not None:
            data["fusion_diagnostics"] = fusion_diagnostics

        return ToolResult(
            ok=True,
            code=code,
            message=message,
            data=data,
            fallback_used=used_geo_fallback,
        )
    finally:
        if own_session:
            await session.close()
