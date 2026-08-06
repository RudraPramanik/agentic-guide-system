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


class TripEditValidationError(WandrError):
    """422 — validation or business rule failed; trip unchanged."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "trip_edit_validation_failed",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=422,
            details=details or {},
        )


class TripStopConflictError(WandrError):
    """409 — place already on trip."""

    def __init__(self, message: str = "stop already on trip") -> None:
        super().__init__(
            code="stop_already_on_trip",
            message=message,
            status_code=409,
        )


class TripStopNotFoundError(WandrError):
    """404 — place_id not on that day."""

    def __init__(self, message: str = "stop not found on this day") -> None:
        super().__init__(
            code="stop_not_found_on_day",
            message=message,
            status_code=404,
        )
