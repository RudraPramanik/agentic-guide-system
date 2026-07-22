"""Destination domain Pydantic schemas — pure data, no model/repository/geo imports."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DestinationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    country: str
    display_name: str
    lat: float
    lng: float
    place_count: int = 0
    created_at: datetime


class DestinationSearchQuery(BaseModel):
    q: str = Field(min_length=2, max_length=200)


class DestinationReadinessOut(BaseModel):
    destination_id: uuid.UUID
    score: float
    tier: Literal["ready", "limited", "sparse"]
    place_count: int
    enriched_pct: float
    indexed_pct: float
    message: str | None = None
