"""Planner HTTP request schemas (P6.2)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    """Body for POST /api/v1/planner/generate."""

    destination_id: UUID
    raw_input: str = Field(min_length=1)
    days: int | None = None
    base_lat: float | None = None
    base_lng: float | None = None
    accommodation_label: str | None = None  # display-only; not persisted as Trip column


class PlannerRunOut(BaseModel):
    """Body for GET /api/v1/planner/runs/{run_id}. Omits key, hash, and session."""

    run_id: UUID
    status: str
    failure_code: str | None = None
    trip_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
