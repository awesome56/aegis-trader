"""Auto-trading policy repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.auto_trading import AutoTradingPolicy
from app.models.enums import BrokerEnvironment
from app.repositories.base import BaseRepository


class AutoTradingPolicyRepository(BaseRepository[AutoTradingPolicy]):
    model = AutoTradingPolicy

    async def get_for_account(
        self, user_id: uuid.UUID, broker_account_id: uuid.UUID
    ) -> AutoTradingPolicy | None:
        stmt = (
            select(AutoTradingPolicy)
            .where(
                AutoTradingPolicy.user_id == user_id,
                AutoTradingPolicy.broker_account_id == broker_account_id,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[AutoTradingPolicy]:
        stmt = select(AutoTradingPolicy).where(AutoTradingPolicy.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_environment(
        self, user_id: uuid.UUID, environment: BrokerEnvironment
    ) -> AutoTradingPolicy | None:
        stmt = (
            select(AutoTradingPolicy)
            .where(
                AutoTradingPolicy.user_id == user_id,
                AutoTradingPolicy.environment == environment,
                AutoTradingPolicy.broker_account_id.is_(None),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
