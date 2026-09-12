"""Strategy and strategy-signal repositories."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select

from app.models.enums import SignalDirection
from app.models.strategy import Strategy, StrategySignal
from app.repositories.base import BaseRepository


class StrategyRepository(BaseRepository[Strategy]):
    model = Strategy

    async def get_by_slug(self, slug: str) -> Strategy | None:
        stmt = select(Strategy).where(Strategy.slug == slug).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, *, enabled_only: bool = False) -> list[Strategy]:
        stmt = select(Strategy).order_by(Strategy.priority.asc(), Strategy.slug.asc())
        if enabled_only:
            stmt = stmt.where(Strategy.is_enabled.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class StrategySignalRepository(BaseRepository[StrategySignal]):
    model = StrategySignal

    async def exists(
        self,
        *,
        strategy_id: uuid.UUID,
        symbol: str,
        timeframe: str,
        direction: SignalDirection,
        data_timestamp: datetime,
    ) -> bool:
        stmt = (
            select(StrategySignal.id)
            .where(
                StrategySignal.strategy_id == strategy_id,
                StrategySignal.symbol == symbol,
                StrategySignal.timeframe == timeframe,
                StrategySignal.direction == direction,
                StrategySignal.data_timestamp == data_timestamp,
            )
            .limit(1)
        )
        return await self.session.scalar(stmt) is not None

    async def list_signals(
        self,
        *,
        strategy_id: uuid.UUID | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        direction: SignalDirection | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StrategySignal]:
        stmt = self._filtered(
            strategy_id=strategy_id,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            start=start,
            end=end,
        )
        stmt = stmt.order_by(StrategySignal.signal_time.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_signals(
        self,
        *,
        strategy_id: uuid.UUID | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
        direction: SignalDirection | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int:
        stmt = self._filtered(
            strategy_id=strategy_id,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            start=start,
            end=end,
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        return int(await self.session.scalar(count_stmt) or 0)

    async def stats_for_strategy(self, strategy_id: uuid.UUID) -> tuple[int, datetime | None]:
        stmt = select(func.count(), func.max(StrategySignal.signal_time)).where(
            StrategySignal.strategy_id == strategy_id
        )
        row = (await self.session.execute(stmt)).one()
        return int(row[0] or 0), row[1]

    def _filtered(
        self,
        *,
        strategy_id: uuid.UUID | None,
        symbol: str | None,
        timeframe: str | None,
        direction: SignalDirection | None,
        start: datetime | None,
        end: datetime | None,
    ):  # noqa: ANN202
        stmt = select(StrategySignal)
        if strategy_id is not None:
            stmt = stmt.where(StrategySignal.strategy_id == strategy_id)
        if symbol is not None:
            stmt = stmt.where(StrategySignal.symbol == symbol.strip().upper())
        if timeframe is not None:
            stmt = stmt.where(StrategySignal.timeframe == timeframe)
        if direction is not None:
            stmt = stmt.where(StrategySignal.direction == direction)
        if start is not None:
            stmt = stmt.where(StrategySignal.signal_time >= start)
        if end is not None:
            stmt = stmt.where(StrategySignal.signal_time <= end)
        return stmt
