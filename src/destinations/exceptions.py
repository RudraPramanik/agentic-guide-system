"""Destination domain exceptions."""

from src.core.exceptions import NotFoundError


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
