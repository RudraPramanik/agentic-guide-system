"""Typed errors for search-area construction."""

from __future__ import annotations


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
