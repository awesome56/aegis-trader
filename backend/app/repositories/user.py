"""User and session repositories."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.models.user import User, UserSession
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class UserSessionRepository(BaseRepository[UserSession]):
    model = UserSession

    async def get_active_by_jti(self, jti: str) -> UserSession | None:
        stmt = select(UserSession).where(
            UserSession.refresh_token_jti == jti,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(UTC),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
