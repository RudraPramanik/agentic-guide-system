"""Auth service — Google OAuth + user upsert. No FastAPI imports."""

from __future__ import annotations

import uuid

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.auth.exceptions import GoogleOAuthError
from src.auth.models import User
from src.auth.repository import UserRepository
from src.config import get_settings
from src.core.exceptions import UnauthorizedError

log = structlog.get_logger()

_HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)


class AuthService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)

    async def upsert_google_user(
        self,
        google_id: str,
        email: str,
        name: str,
        avatar_url: str | None,
    ) -> User:
        """
        Find user by google_id → fall back to email lookup → create if not found.
        Update avatar_url and google_id if they changed.
        Commits the transaction — auth upsert is always a standalone operation.
        """
        user = await self.repo.get_by_google_id(google_id)
        if user is None:
            user = await self.repo.get_by_email(email)

        if user is None:
            user = await self.repo.create(
                {
                    "google_id": google_id,
                    "email": email,
                    "name": name,
                    "avatar_url": avatar_url,
                    "is_active": True,
                }
            )
            log.info("auth.user_created", email=email)
        else:
            updates: dict = {}
            if user.google_id != google_id:
                updates["google_id"] = google_id
            if user.avatar_url != avatar_url:
                updates["avatar_url"] = avatar_url
            if updates:
                await self.repo.update(user.id, updates)
                log.info(
                    "auth.user_updated",
                    user_id=str(user.id),
                    fields=list(updates.keys()),
                )

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.repo.get_by_id(user_id)

    async def verify_google_token(self, access_token: str) -> dict:
        """
        Verify a Google access token via Google's userinfo endpoint.
        Returns the userinfo dict on success.
        Raises GoogleOAuthError on network failure after retries.
        Raises UnauthorizedError if Google rejects the token (no retry on 401).
        """
        return await self._fetch_google_userinfo(access_token)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True,
    )
    async def _fetch_google_userinfo(self, access_token: str) -> dict:
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    settings.GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if response.status_code in (400, 401):
                    raise UnauthorizedError("Google rejected the access token")
                response.raise_for_status()
                return response.json()
        except UnauthorizedError:
            raise
        except httpx.HTTPStatusError as e:
            raise GoogleOAuthError(
                f"Google OAuth returned {e.response.status_code}",
                details={"status": e.response.status_code},
            )
        except httpx.RequestError as e:
            raise GoogleOAuthError(
                f"Google OAuth connection error: {type(e).__name__}"
            )

    async def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str,
        client_id: str,
        client_secret: str,
    ) -> str:
        """
        Exchange an OAuth authorization code for a Google access token.
        Returns the access_token string.
        Raises GoogleOAuthError on any failure after retries.
        """
        return await self._post_google_token_exchange(
            code, redirect_uri, client_id, client_secret
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True,
    )
    async def _post_google_token_exchange(
        self,
        code: str,
        redirect_uri: str,
        client_id: str,
        client_secret: str,
    ) -> str:
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(
                    settings.GOOGLE_TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                response.raise_for_status()
                data = response.json()
                access_token = data.get("access_token")
                if not access_token:
                    raise GoogleOAuthError("No access_token in Google token response")
                return access_token
        except GoogleOAuthError:
            raise
        except httpx.HTTPStatusError as e:
            raise GoogleOAuthError(
                f"Google token exchange failed: {e.response.status_code}"
            )
        except httpx.RequestError as e:
            raise GoogleOAuthError(
                f"Google token exchange connection error: {type(e).__name__}"
            )
