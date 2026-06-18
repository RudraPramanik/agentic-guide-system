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


class WandrLLMError(WandrError):
    """Raised only by core/llm/client.py after LLM retries are exhausted."""

    def __init__(
        self,
        code: str = "llm_unavailable",
        message: str = "LLM service unavailable",
        details: dict | None = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=503, details=details)
