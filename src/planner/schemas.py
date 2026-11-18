"""Planner HTTP request schemas (P6.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DiscoveryAnchorIn(BaseModel):
    """Optional client selection. Server rebuilds the search area; never trusted as stored JSON."""

    canonical_name: str
    location_type: str
    lat: float
    lng: float
    provider: Literal["nominatim", "catalog", "user"]
    query: str | None = None
    provider_id: str | None = None


class PlanRequest(BaseModel):
    """Body for POST /api/v1/planner/generate."""

    destination_id: UUID
    raw_input: str = Field(min_length=1)
    days: int | None = Field(default=None, ge=1, le=30)
    base_lat: float | None = None
    base_lng: float | None = None
    accommodation_label: str | None = None  # display-only; not persisted as Trip column
    discovery_anchor: DiscoveryAnchorIn | None = None
    radius_km: float | None = None


class PlannerRunOut(BaseModel):
    """Body for GET /api/v1/planner/runs/{run_id}. Omits key, hash, and session."""

    run_id: UUID
    status: str
    failure_code: str | None = None
    trip_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


def location_key_suffix(body: PlanRequest) -> str:
    """Suffix for idempotency / cache when the body posted an anchor or radius."""
    parts: list[str] = []
    anchor = body.discovery_anchor
    if anchor is not None:
        parts.append(
            f"a:{anchor.provider}:{anchor.provider_id or ''}:"
            f"{anchor.location_type}:{round(anchor.lat, 5)}:{round(anchor.lng, 5)}"
        )
    if body.radius_km is not None:
        parts.append(f"r:{round(float(body.radius_km), 3)}")
    return "|".join(parts)
