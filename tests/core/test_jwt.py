"""Unit tests for JWT create/verify."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt as jose_jwt

from src.config import get_settings
from src.core.security.jwt import create_access_token, verify_token


def test_create_and_verify_round_trip() -> None:
    uid = uuid.uuid4()
    token = create_access_token(uid, "test@wandr.dev")
    payload = verify_token(token)
    assert payload is not None
    assert payload.user_id == uid
    assert payload.email == "test@wandr.dev"
    assert payload.exp.tzinfo is not None


def test_verify_invalid_tokens_return_none() -> None:
    assert verify_token("not.a.token") is None
    assert verify_token("") is None
    assert verify_token("a.b.c") is None


def test_verify_expired_token_returns_none() -> None:
    uid = uuid.uuid4()
    expired = jose_jwt.encode(
        {
            "sub": str(uid),
            "email": "x@x.com",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        get_settings().SECRET_KEY,
        algorithm="HS256",
    )
    assert verify_token(expired) is None
