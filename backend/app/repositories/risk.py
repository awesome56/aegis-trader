"""Risk settings, system-state and risk-evaluation repositories."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select

from app.models.proposal import RiskEvaluation
from app.models.risk import RiskSettings
from app.models.system import SystemState
from app.repositories.base import BaseRepository


class RiskSettingsRepository(BaseRepository[RiskSettings]):
    model = RiskSettings

    async def get_for_user(self, user_id: uuid.UUID) -> RiskSettings | None:
        stmt = select(RiskSettings).where(RiskSettings.user_id == user_id).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class SystemStateRepository(BaseRepository[SystemState]):
    model = SystemState

    async def get_by_key(self, key: str = "trading") -> SystemState | None:
        stmt = select(SystemState).where(SystemState.key == key).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class RiskEvaluationRepository(BaseRepository[RiskEvaluation]):
    model = RiskEvaluation

    async def list_evaluations(
        self,
        *,
        portfolio_id: uuid.UUID | None = None,
        symbol: str | None = None,
        decision: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RiskEvaluation]:
        stmt = self._filtered(
            portfolio_id=portfolio_id, symbol=symbol, decision=decision, start=start, end=end
        )
        stmt = stmt.order_by(RiskEvaluation.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_evaluations(
        self,
        *,
        portfolio_id: uuid.UUID | None = None,
        symbol: str | None = None,
        decision: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int:
        stmt = self._filtered(
            portfolio_id=portfolio_id, symbol=symbol, decision=decision, start=start, end=end
        )
        return int(
            await self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        )

    def _filtered(
        self,
        *,
        portfolio_id: uuid.UUID | None,
        symbol: str | None,
        decision: str | None,
        start: datetime | None,
        end: datetime | None,
    ):  # noqa: ANN202
        stmt = select(RiskEvaluation)
        if portfolio_id is not None:
            stmt = stmt.where(RiskEvaluation.portfolio_id == portfolio_id)
        if symbol is not None:
            stmt = stmt.where(RiskEvaluation.symbol == symbol.strip().upper())
        if decision is not None:
            stmt = stmt.where(RiskEvaluation.decision == decision)
        if start is not None:
            stmt = stmt.where(RiskEvaluation.created_at >= start)
        if end is not None:
            stmt = stmt.where(RiskEvaluation.created_at <= end)
        return stmt
