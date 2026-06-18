"""Tests for src/core/exceptions.py."""

from src.core.exceptions import (
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    WandrError,
    WandrLLMError,
)


def test_not_found_error_defaults() -> None:
    exc = NotFoundError("Destination not found", details={"id": "abc"})
    assert exc.status_code == 404
    assert exc.code == "not_found"
    assert exc.message == "Destination not found"
    assert exc.details == {"id": "abc"}
    assert isinstance(exc, WandrError)


def test_wandr_llm_error() -> None:
    exc = WandrLLMError(code="llm_unavailable", message="LLM timed out after retries")
    assert exc.status_code == 503
    assert exc.code == "llm_unavailable"
    assert isinstance(exc, WandrError)


def test_external_service_error_includes_service_in_details() -> None:
    exc = ExternalServiceError(service="nominatim", message="Geocode failed")
    assert exc.status_code == 502
    assert exc.details == {"service": "nominatim"}


def test_unauthorized_error() -> None:
    exc = UnauthorizedError()
    assert exc.status_code == 401
    assert exc.code == "unauthorized"
    assert exc.message == "Authentication required"


def test_forbidden_error() -> None:
    exc = ForbiddenError()
    assert exc.status_code == 403
    assert exc.code == "forbidden"
    assert exc.message == "Access denied"


def test_external_service_error_merges_details() -> None:
    exc = ExternalServiceError(
        service="osrm",
        message="Routing failed",
        details={"status": 503},
    )
    assert exc.details == {"service": "osrm", "status": 503}
