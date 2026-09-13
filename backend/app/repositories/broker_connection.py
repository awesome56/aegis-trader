"""Broker connection repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select, update

from app.models.broker_connection import BrokerConnection
from app.models.enums import BrokerEnvironment
from app.repositories.base import BaseRepository


class BrokerConnectionRepository(BaseRepository[BrokerConnection]):
    model = BrokerConnection

    async def list_for_user(self, user_id: uuid.UUID) -> list[BrokerConnection]:
        stmt = (
            select(BrokerConnection)
            .where(BrokerConnection.user_id == user_id)
            .order_by(BrokerConnection.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_user(
        self, connection_id: uuid.UUID, user_id: uuid.UUID
    ) -> BrokerConnection | None:
        stmt = select(BrokerConnection).where(
            BrokerConnection.id == connection_id, BrokerConnection.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default(
        self, user_id: uuid.UUID, environment: BrokerEnvironment
    ) -> BrokerConnection | None:
        stmt = (
            select(BrokerConnection)
            .where(
                BrokerConnection.user_id == user_id,
                BrokerConnection.environment == environment,
                BrokerConnection.is_default.is_(True),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def clear_defaults(self, user_id: uuid.UUID, environment: BrokerEnvironment) -> None:
        await self.session.execute(
            update(BrokerConnection)
            .where(
                BrokerConnection.user_id == user_id,
                BrokerConnection.environment == environment,
                BrokerConnection.is_default.is_(True),
            )
            .values(is_default=False)
            .execution_options(synchronize_session=False)
        )
