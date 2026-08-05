"""Destination domain exceptions."""

from src.core.exceptions import NotFoundError, WandrError


class DestinationNotFoundError(NotFoundError):
    def __init__(
        self,
        query: str | None = None,
        destination_id: str | None = None,
    ) -> None:
        details: dict = {}
        if query:
            details["query"] = query
        if destination_id:
            details["destination_id"] = destination_id
        super().__init__(
            message="Destination not found",
            details=details or None,
        )


class DestinationNotReadyError(WandrError):
    """place_count below PLANNER_ABSOLUTE_MIN_PLACES — refuse generation (409)."""

    def __init__(self, place_count: int) -> None:
        super().__init__(
            code="destination_not_ready",
            message="Destination does not have enough places for planning",
            status_code=409,
            details={"place_count": place_count},
        )
