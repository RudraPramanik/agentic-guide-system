"""Unit tests for auth schemas and exceptions."""

from src.auth.exceptions import AccountInactiveError, GoogleOAuthError, InvalidTokenError
from src.auth.schemas import AuthMeResponse


def test_guest_auth_me_response() -> None:
    r = AuthMeResponse(is_guest=True, session_id="test-session-123")
    assert r.user is None
    assert r.is_guest is True


def test_google_oauth_error() -> None:
    e = GoogleOAuthError("timeout")
    assert e.status_code == 502
    assert e.details["service"] == "google_oauth"


def test_invalid_token_error() -> None:
    e = InvalidTokenError()
    assert e.status_code == 401


def test_account_inactive_error() -> None:
    e = AccountInactiveError()
    assert e.status_code == 401
    assert "deactivated" in e.message.lower()
