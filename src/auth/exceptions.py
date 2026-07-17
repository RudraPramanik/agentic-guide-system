"""Auth-specific exceptions — inherit from WandrError subclasses only."""

from src.core.exceptions import ExternalServiceError, UnauthorizedError


class GoogleOAuthError(ExternalServiceError):
    """Raised when Google OAuth token exchange or userinfo call fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(service="google_oauth", message=message, details=details)


class InvalidTokenError(UnauthorizedError):
    """Raised when a token is present but fails verification."""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message=message)


class AccountInactiveError(UnauthorizedError):
    """Raised when a valid token belongs to a deactivated user."""

    def __init__(self):
        super().__init__(message="Account is deactivated")
