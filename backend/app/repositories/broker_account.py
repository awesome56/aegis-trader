"""Broker account repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.broker import BrokerAccount
from app.models.enums import BrokerEnvironment, BrokerMode
from app.repositories.base import BaseRepository


class BrokerAccountRepository(BaseRepository[BrokerAccount]):
    model = BrokerAccount

    async def get_active_for_user(
        self,
        user_id: uuid.UUID,
        *,
        broker: str = "paper",
        mode: BrokerMode = BrokerMode.PAPER,
    ) -> BrokerAccount | None:
        stmt = (
            select(BrokerAccount)
            .where(
                BrokerAccount.user_id == user_id,
                BrokerAccount.broker == broker,
                BrokerAccount.mode == mode,
                BrokerAccount.is_active.is_(True),
            )
            .order_by(BrokerAccount.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_user(self, account_id: uuid.UUID, user_id: uuid.UUID) -> BrokerAccount | None:
        stmt = select(BrokerAccount).where(
            BrokerAccount.id == account_id, BrokerAccount.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_provider(
        self,
        user_id: uuid.UUID,
        *,
        broker: str,
        environment: BrokerEnvironment,
        external_account_id: str | None = None,
    ) -> BrokerAccount | None:
        stmt = select(BrokerAccount).where(
            BrokerAccount.user_id == user_id,
            BrokerAccount.broker == broker,
            BrokerAccount.environment == environment,
        )
        if external_account_id is not None:
            stmt = stmt.where(BrokerAccount.external_account_id == external_account_id)
        stmt = stmt.order_by(BrokerAccount.created_at.asc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_locked(self, account_id: uuid.UUID) -> BrokerAccount | None:
        """Row-lock the account for a serialised cash/position mutation."""
        stmt = select(BrokerAccount).where(BrokerAccount.id == account_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[BrokerAccount]:
        stmt = (
            select(BrokerAccount)
            .where(BrokerAccount.user_id == user_id)
            .order_by(BrokerAccount.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_active_external(self) -> list[BrokerAccount]:
        """Every active account backed by a real venue adapter (paper excluded)."""
        stmt = (
            select(BrokerAccount)
            .where(
                BrokerAccount.is_active.is_(True),
                BrokerAccount.broker != "paper",
            )
            .order_by(BrokerAccount.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
