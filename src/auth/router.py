"""Auth HTTP router — Google OAuth + me/logout. Calls AuthService only."""

from __future__ import annotations

import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import AccountInactiveError
from src.auth.schemas import AuthMeResponse, TokenResponse, UserOut
from src.auth.service import AuthService
from src.config import Settings, get_settings
from src.core.database.session import get_db
from src.core.exceptions import UnauthorizedError, WandrError
from src.core.responses import ApiResponse
from src.core.security.jwt import TokenPayload, create_access_token
from src.core.security.permissions import optional_auth

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

COOKIE_TOKEN = "wandr_token"
COOKIE_SESSION = "wandr_session"
SESSION_MAX_AGE_SECONDS = 30 * 24 * 3600


def _cookie_secure() -> bool:
    return get_settings().ENVIRONMENT == "production"


def _token_max_age() -> int:
    return get_settings().ACCESS_TOKEN_EXPIRE_DAYS * 24 * 3600


def _frontend_base(settings: Settings) -> str:
    return settings.FRONTEND_URL.rstrip("/") if settings.FRONTEND_URL else ""


def _frontend_auth_url(settings: Settings, path: str, **query: str) -> str | None:
    base = _frontend_base(settings)
    if not base:
        return None
    url = f"{base}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def _set_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_TOKEN,
        token,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        max_age=_token_max_age(),
    )


def _ensure_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get(COOKIE_SESSION) or str(uuid.uuid4())
    response.set_cookie(
        COOKIE_SESSION,
        session_id,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    return session_id


@router.get("/google")
async def google_oauth_start():
    """Start Google OAuth flow, or report when OAuth is not configured."""
    settings = get_settings()
    if not settings.GOOGLE_CLIENT_ID:
        return ApiResponse(data={"message": "Google OAuth not configured"})

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    }
    url = f"{settings.GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/callback")
async def google_oauth_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth redirect from Google; set wandr_token on success."""
    settings = get_settings()

    if error:
        done_url = _frontend_auth_url(settings, "/auth/error", reason=error)
        if done_url:
            return RedirectResponse(url=done_url)
        return RedirectResponse(url=f"/auth/error?reason={error}")

    if not code:
        done_url = _frontend_auth_url(settings, "/auth/error", reason="oauth_failed")
        if done_url:
            return RedirectResponse(url=done_url)
        return RedirectResponse(url="/auth/error?reason=oauth_failed")

    svc = AuthService(db)

    try:
        access_token = await svc.exchange_code_for_token(
            code,
            settings.GOOGLE_REDIRECT_URI,
            settings.GOOGLE_CLIENT_ID,
            settings.GOOGLE_CLIENT_SECRET,
        )
        userinfo = await svc.verify_google_token(access_token)
        user = await svc.upsert_google_user(
            google_id=userinfo["sub"],
            email=userinfo["email"],
            name=userinfo.get("name", userinfo["email"]),
            avatar_url=userinfo.get("picture"),
        )
        token = create_access_token(user.id, user.email)
    except WandrError:
        done_url = _frontend_auth_url(settings, "/auth/error", reason="oauth_failed")
        if done_url:
            return RedirectResponse(url=done_url)
        return RedirectResponse(url="/auth/error?reason=oauth_failed")

    done_url = _frontend_auth_url(settings, "/auth/done")
    if done_url:
        response = RedirectResponse(url=done_url, status_code=302)
        _set_token_cookie(response, token)
        return response

    body = ApiResponse(
        data=TokenResponse(
            access_token=token,
            user=UserOut.model_validate(user),
        )
    )
    response = JSONResponse(content=body.model_dump(mode="json"))
    _set_token_cookie(response, token)
    return response


@router.get("/me", response_model=ApiResponse[AuthMeResponse])
async def auth_me(
    request: Request,
    response: Response,
    payload: TokenPayload | None = Depends(optional_auth),
    db: AsyncSession = Depends(get_db),
):
    """Current user or guest info; ensures httpOnly wandr_session cookie."""
    session_id = _ensure_session_id(request, response)

    if payload is not None:
        user = await AuthService(db).get_user_by_id(payload.user_id)
        if user is None:
            raise UnauthorizedError("User account not found")
        if not user.is_active:
            raise AccountInactiveError()
        return ApiResponse(
            data=AuthMeResponse(
                is_guest=False,
                session_id=session_id,
                user=UserOut.model_validate(user),
            )
        )

    return ApiResponse(
        data=AuthMeResponse(
            is_guest=True,
            session_id=session_id,
            user=None,
        )
    )


@router.post("/logout")
async def logout():
    """Clear auth cookie. No auth required."""
    body = ApiResponse(data={"message": "Logged out"})
    response = JSONResponse(content=body.model_dump(mode="json"))
    response.delete_cookie(COOKIE_TOKEN)
    return response
