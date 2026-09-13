"""Backtest repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.backtest import Backtest, BacktestResult
from app.models.enums import BacktestStatus
from app.repositories.base import BaseRepository


class BacktestRepository(BaseRepository[Backtest]):
    model = Backtest

    async def get_for_user(self, backtest_id: uuid.UUID, user_id: uuid.UUID) -> Backtest | None:
        stmt = select(Backtest).where(
            Backtest.id == backtest_id, Backtest.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_locked(self, backtest_id: uuid.UUID) -> Backtest | None:
        stmt = select(Backtest).where(Backtest.id == backtest_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[Backtest]:
        stmt = (
            select(Backtest)
            .where(Backtest.user_id == user_id)
            .order_by(Backtest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count()).select_from(Backtest).where(Backtest.user_id == user_id)
        )
        return int(await self.session.scalar(stmt) or 0)

    async def count_active_for_user(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Backtest)
            .where(
                Backtest.user_id == user_id,
                Backtest.status.in_([BacktestStatus.PENDING, BacktestStatus.RUNNING]),
            )
        )
        return int(await self.session.scalar(stmt) or 0)


class BacktestResultRepository(BaseRepository[BacktestResult]):
    model = BacktestResult

    async def get_for_backtest(self, backtest_id: uuid.UUID) -> BacktestResult | None:
        stmt = select(BacktestResult).where(BacktestResult.backtest_id == backtest_id).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
