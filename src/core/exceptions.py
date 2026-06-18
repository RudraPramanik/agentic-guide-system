"""Wandr — application exception hierarchy."""


class WandrError(Exception):
    """Base exception for all Wandr domain errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: dict | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(WandrError):
    """Resource not found (404)."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            code="not_found",
            message=message,
            status_code=404,
            details=details,
        )


class UnauthorizedError(WandrError):
    """Authentication required (401)."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            code="unauthorized",
            message=message,
            status_code=401,
        )


class ForbiddenError(WandrError):
    """Access denied (403)."""

    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(
            code="forbidden",
            message=message,
            status_code=403,
        )


class ExternalServiceError(WandrError):
    """Upstream external service failure (502)."""

    def __init__(
        self,
        service: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        super().__init__(
            code="external_service_error",
            message=message,
            status_code=502,
            details={"service": service, **(details or {})},
        )


class WandrLLMError(WandrError):
    """LLM unavailable after retries (503). Raised only by core/llm/client.py."""

    def __init__(
        self,
        code: str = "llm_unavailable",
        message: str = "LLM service unavailable",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=503,
            details=details,
        )
