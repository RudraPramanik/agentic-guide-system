"""JWT creation and verification (HS256)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jose import ExpiredSignatureError, JWTError, jwt

from src.config import get_settings

ALGORITHM = "HS256"


@dataclass
class TokenPayload:
    user_id: uuid.UUID
    email: str
    exp: datetime


def create_access_token(user_id: uuid.UUID, email: str) -> str:
    """Create a signed HS256 JWT. Expiry from ACCESS_TOKEN_EXPIRE_DAYS settings."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> TokenPayload | None:
    """
    Decode and validate a JWT. Returns TokenPayload on success, None on any failure.
    NEVER raises — all exceptions are caught and return None.
    """
    try:
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        email = payload.get("email")
        exp_raw = payload.get("exp")
        if not sub or not email or not exp_raw:
            return None
        return TokenPayload(
            user_id=uuid.UUID(sub),
            email=email,
            exp=datetime.fromtimestamp(exp_raw, tz=timezone.utc),
        )
    except (JWTError, ExpiredSignatureError, ValueError, KeyError, Exception):
        return None
