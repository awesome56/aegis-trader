"""Position repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.position import Position
from app.repositories.base import BaseRepository


class PositionRepository(BaseRepository[Position]):
    model = Position

    async def get_open(
        self, portfolio_id: uuid.UUID, symbol: str, *, for_update: bool = False
    ) -> Position | None:
        stmt = select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.symbol == symbol.strip().upper(),
            Position.is_open.is_(True),
        )
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def get_open_by_id(
        self, position_id: uuid.UUID, portfolio_id: uuid.UUID
    ) -> Position | None:
        stmt = select(Position).where(
            Position.id == position_id, Position.portfolio_id == portfolio_id
        )
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def list_open(self, portfolio_id: uuid.UUID) -> list[Position]:
        stmt = (
            select(Position)
            .where(Position.portfolio_id == portfolio_id, Position.is_open.is_(True))
            .order_by(Position.symbol.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_open(self, portfolio_id: uuid.UUID) -> int:
        positions = await self.list_open(portfolio_id)
        return len(positions)
