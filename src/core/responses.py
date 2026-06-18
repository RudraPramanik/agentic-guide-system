"""Wandr — standard API response envelope models."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Success envelope for single-resource endpoints."""

    success: bool = True
    data: T
    message: str | None = None


class ErrorResponse(BaseModel):
    """Error envelope for the global exception handler."""

    success: bool = False
    code: str
    message: str
    details: dict | None = None
