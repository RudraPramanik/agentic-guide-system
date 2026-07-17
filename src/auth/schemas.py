"""Auth domain Pydantic schemas — pure data, no model/repository imports."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserOut(BaseModel):
    """Public representation of a User. Used in all auth responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str
    avatar_url: str | None
    is_active: bool
    created_at: datetime


class AuthMeResponse(BaseModel):
    """
    Response for GET /auth/me — works for both guests and authenticated users.
    Guests: is_guest=True, user=None, session_id set.
    Authenticated: is_guest=False, user=UserOut, session_id set.
    """

    is_guest: bool
    session_id: str
    user: UserOut | None = None


class TokenResponse(BaseModel):
    """Returned after successful OAuth callback."""

    access_token: str
    token_type: str = "bearer"
    user: UserOut


class GoogleCallbackParams(BaseModel):
    """Query params received from Google on OAuth callback."""

    code: str
    state: str | None = None
    error: str | None = None
