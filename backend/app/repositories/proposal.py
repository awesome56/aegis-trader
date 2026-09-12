"""TradeProposal repository."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.enums import ProposalStatus
from app.models.proposal import TradeProposal
from app.repositories.base import BaseRepository


class TradeProposalRepository(BaseRepository[TradeProposal]):
    model = TradeProposal

    async def get_by_idempotency_key(self, key: str) -> TradeProposal | None:
        stmt = select(TradeProposal).where(TradeProposal.idempotency_key == key).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_locked(self, proposal_id: uuid.UUID) -> TradeProposal | None:
        stmt = (
            select(TradeProposal)
            .where(TradeProposal.id == proposal_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_portfolio(
        self,
        portfolio_id: uuid.UUID,
        *,
        status: ProposalStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TradeProposal]:
        stmt = select(TradeProposal).where(TradeProposal.portfolio_id == portfolio_id)
        if status is not None:
            stmt = stmt.where(TradeProposal.status == status)
        stmt = stmt.order_by(TradeProposal.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_portfolio(
        self, portfolio_id: uuid.UUID, *, status: ProposalStatus | None = None
    ) -> int:
        stmt = select(func.count()).select_from(TradeProposal).where(
            TradeProposal.portfolio_id == portfolio_id
        )
        if status is not None:
            stmt = stmt.where(TradeProposal.status == status)
        return int(await self.session.scalar(stmt) or 0)
