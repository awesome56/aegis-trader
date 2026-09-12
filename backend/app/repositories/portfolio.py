"""Portfolio and portfolio-snapshot repositories."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from app.models.portfolio import Portfolio, PortfolioSnapshot
from app.repositories.base import BaseRepository


class PortfolioRepository(BaseRepository[Portfolio]):
    model = Portfolio

    async def get_default_for_user(self, user_id: uuid.UUID) -> Portfolio | None:
        stmt = (
            select(Portfolio)
            .where(Portfolio.user_id == user_id, Portfolio.is_active.is_(True))
            .order_by(Portfolio.is_default.desc(), Portfolio.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_user(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> Portfolio | None:
        stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()


class PortfolioSnapshotRepository(BaseRepository[PortfolioSnapshot]):
    model = PortfolioSnapshot

    async def latest(self, portfolio_id: uuid.UUID) -> PortfolioSnapshot | None:
        stmt = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio_id)
            .order_by(PortfolioSnapshot.snapshot_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def latest_before(
        self, portfolio_id: uuid.UUID, before: datetime
    ) -> PortfolioSnapshot | None:
        stmt = (
            select(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.portfolio_id == portfolio_id,
                PortfolioSnapshot.snapshot_time < before,
            )
            .order_by(PortfolioSnapshot.snapshot_time.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def peak_equity(self, portfolio_id: uuid.UUID) -> object:
        from sqlalchemy import func

        stmt = select(func.max(PortfolioSnapshot.equity)).where(
            PortfolioSnapshot.portfolio_id == portfolio_id
        )
        return await self.session.scalar(stmt)

    async def list_range(
        self,
        portfolio_id: uuid.UUID,
        start: datetime | None = None,
        end: datetime | None = None,
        *,
        limit: int = 5000,
    ) -> list[PortfolioSnapshot]:
        stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio_id)
        if start is not None:
            stmt = stmt.where(PortfolioSnapshot.snapshot_time >= start)
        if end is not None:
            stmt = stmt.where(PortfolioSnapshot.snapshot_time <= end)
        stmt = stmt.order_by(PortfolioSnapshot.snapshot_time.asc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
