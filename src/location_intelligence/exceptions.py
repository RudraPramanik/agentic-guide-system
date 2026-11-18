"""Typed errors for search-area construction and HTTP mapping."""

from __future__ import annotations

from src.core.exceptions import WandrError


class LocationIntelligenceError(Exception):
    """Base for location-intelligence domain errors."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class OversizedAdminError(LocationIntelligenceError):
    """Country or region must not become a radius search area."""

    def __init__(self, location_type: str) -> None:
        super().__init__(
            code="oversized_admin",
            message=f"Cannot build a search area for {location_type}; pick a city hub",
        )


class InvalidPolygonError(LocationIntelligenceError):
    """Supplied GeoJSON failed shape checks."""

    def __init__(self, message: str = "Invalid polygon geometry") -> None:
        super().__init__(code="invalid_polygon", message=message)


class LocationValidationError(WandrError):
    """422 — location request failed a named business rule."""

    def __init__(self, code: str, message: str, *, details: dict | None = None) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=422,
            details=details or {},
        )


class AnchorNotConfirmedError(LocationValidationError):
    def __init__(self, message: str = "Posted anchor was not in the candidate list") -> None:
        super().__init__(code="anchor_not_confirmed", message=message)


class InvalidCoordinatesError(LocationValidationError):
    def __init__(self, message: str = "Latitude or longitude out of range") -> None:
        super().__init__(code="invalid_coordinates", message=message)


def as_http_error(exc: LocationIntelligenceError) -> LocationValidationError:
    """Map a pure library error onto the envelope used by routers."""
    return LocationValidationError(code=exc.code, message=exc.message)
