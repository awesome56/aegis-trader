"""Authentication service: registration, login, token rotation, logout."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError, ConflictError
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserSession
from app.repositories.user import UserRepository, UserSessionRepository


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.users = UserRepository(session)
        self.sessions = UserSessionRepository(session)

    async def registration_open(self) -> bool:
        """Personal deployments allow bootstrap registration until one user exists."""
        return await self.users.count() == 0

    async def register(self, email: str, password: str, full_name: str | None = None) -> User:
        if not await self.registration_open():
            raise AuthorizationError("Registration is closed")
        if len(password) < self.settings.PASSWORD_MIN_LENGTH:
            raise ConflictError(
                f"Password must be at least {self.settings.PASSWORD_MIN_LENGTH} characters"
            )
        existing = await self.users.get_by_email(email)
        if existing is not None:
            raise ConflictError("Email is already registered")
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            full_name=full_name,
            is_active=True,
            is_superuser=True,  # first (bootstrap) user is the owner
        )
        return await self.users.add(user)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
        return user

    async def _issue_tokens(
        self, user: User, device_name: str | None, ip_address: str | None, user_agent: str | None
    ) -> tuple[str, str]:
        access_token = create_access_token(str(user.id), self.settings)
        refresh_token = create_refresh_token(str(user.id), self.settings)
        payload = decode_token(refresh_token, expected_type="refresh", settings=self.settings)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        session = UserSession(
            user_id=user.id,
            refresh_token_jti=payload["jti"],
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
            last_used_at=datetime.now(UTC),
        )
        await self.sessions.add(session)
        return access_token, refresh_token

    async def login(
        self,
        email: str,
        password: str,
        *,
        device_name: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
        user = await self.authenticate(email, password)
        user.last_login_at = datetime.now(UTC)
        access_token, refresh_token = await self._issue_tokens(
            user, device_name, ip_address, user_agent
        )
        return user, access_token, refresh_token

    async def refresh(
        self, refresh_token: str, *, ip_address: str | None = None, user_agent: str | None = None
    ) -> tuple[User, str, str]:
        try:
            payload = decode_token(refresh_token, expected_type="refresh", settings=self.settings)
        except TokenError as exc:
            raise AuthenticationError("Invalid refresh token") from exc

        session = await self.sessions.get_active_by_jti(payload["jti"])
        if session is None:
            raise AuthenticationError("Refresh token is not active")

        user = await self.users.get(session.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Account is disabled")

        # Rotate: revoke the old session, then issue a new pair.
        session.revoked_at = datetime.now(UTC)
        return user, *await self._issue_tokens(user, session.device_name, ip_address, user_agent)

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token, settings=self.settings)
        except TokenError:
            return
        session = await self.sessions.get_active_by_jti(payload["jti"])
        if session is not None:
            session.revoked_at = datetime.now(UTC)

    async def list_sessions(self, user_id: uuid.UUID) -> list[UserSession]:
        return await self.sessions.list(user_id=user_id, order_by="created_at", limit=100)
