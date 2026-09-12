"""Worker persistence unit-of-work and market-data wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session_factory
from app.market.services.market_data import MarketDataService
from app.models.user import User
from app.realtime.publisher import publish_pending


@asynccontextmanager
async def worker_session() -> AsyncIterator[AsyncSession]:
    """Commit on success, roll back on error, publish events post-commit."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        await publish_pending(session.info)


def build_market_service(session: AsyncSession) -> MarketDataService:
    return MarketDataService(session)


async def active_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).where(User.is_active.is_(True)))
    return list(result.scalars().all())
