"""Trip domain exceptions."""

from __future__ import annotations

from src.core.exceptions import ForbiddenError, NotFoundError, WandrError


class TripNotFoundError(NotFoundError):
    def __init__(self, trip_id: str | None = None) -> None:
        details = {"trip_id": trip_id} if trip_id else None
        super().__init__(message="Trip not found", details=details)


class TripForbiddenError(ForbiddenError):
    def __init__(self, message: str = "Access to this trip is forbidden") -> None:
        super().__init__(message=message)


class TripAlreadyClaimedError(WandrError):
    def __init__(self, trip_id: str | None = None) -> None:
        details = {"trip_id": trip_id} if trip_id else None
        super().__init__(
            code="trip_already_claimed",
            message="Trip has already been claimed",
            status_code=409,
            details=details,
        )
