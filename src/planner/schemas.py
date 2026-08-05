"""Planner HTTP request schemas (P6.2)."""

from __future__ import annotations

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
