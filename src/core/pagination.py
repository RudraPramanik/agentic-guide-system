"""Wandr — shared pagination models for list endpoints."""

from __future__ import annotations

import math
from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, model_validator

T = TypeVar("T")


class PageParams(BaseModel):
    """FastAPI dependency for incoming pagination query parameters."""

    page: Annotated[int, Query(ge=1)] = 1
    size: Annotated[int, Query(ge=1, le=100)] = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list response for all list endpoints."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int = 1
    has_next: bool = False
    has_prev: bool = False

    @model_validator(mode="after")
    def _compute_pagination_metadata(self) -> PaginatedResponse[T]:
        pages = max(1, math.ceil(self.total / self.size) if self.size else 1)
        self.pages = pages
        self.has_next = self.page < pages
        self.has_prev = self.page > 1
        return self


def paginate(items: list[T], total: int, params: PageParams) -> PaginatedResponse[T]:
    """Build a PaginatedResponse from a page of items and query params."""

    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        size=params.size,
    )
