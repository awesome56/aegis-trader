"""Order and execution repositories."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.models.enums import OrderStatus, TradeSide
from app.models.order import Execution, Order
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    model = Order

    async def get_by_idempotency_key(
        self, key: str, broker_account_id: uuid.UUID | None = None
    ) -> Order | None:
        stmt = select(Order).where(Order.idempotency_key == key)
        if broker_account_id is not None:
            stmt = stmt.where(Order.broker_account_id == broker_account_id)
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def get_scoped(self, order_id: uuid.UUID, broker_account_id: uuid.UUID) -> Order | None:
        stmt = select(Order).where(
            Order.id == order_id, Order.broker_account_id == broker_account_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_account(
        self,
        broker_account_id: uuid.UUID,
        *,
        status: OrderStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        stmt = select(Order).where(Order.broker_account_id == broker_account_id)
        if status is not None:
            stmt = stmt.where(Order.status == status)
        stmt = stmt.order_by(Order.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_account(
        self, broker_account_id: uuid.UUID, *, status: OrderStatus | None = None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Order)
            .where(Order.broker_account_id == broker_account_id)
        )
        if status is not None:
            stmt = stmt.where(Order.status == status)
        return int(await self.session.scalar(stmt) or 0)

    async def count_created_since(self, broker_account_id: uuid.UUID, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(Order)
            .where(
                Order.broker_account_id == broker_account_id,
                Order.created_at >= since,
            )
        )
        return int(await self.session.scalar(stmt) or 0)

    async def list_open_for_account(self, broker_account_id: uuid.UUID) -> list[Order]:
        """Orders that are still working (including partially filled)."""
        open_statuses = [
            OrderStatus.CREATED,
            OrderStatus.VALIDATED,
            OrderStatus.SUBMITTED,
            OrderStatus.ACCEPTED,
            OrderStatus.PARTIALLY_FILLED,
        ]
        stmt = (
            select(Order)
            .where(
                Order.broker_account_id == broker_account_id,
                Order.status.in_(open_statuses),
            )
            .order_by(Order.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def reserved_buy_notional(self, broker_account_id: uuid.UUID) -> Decimal:
        """Sum of remaining notional across open BUY orders (buying-power reserve)."""
        orders = await self.list_open_for_account(broker_account_id)
        total = Decimal("0")
        for order in orders:
            if order.side is not TradeSide.BUY:
                continue
            remaining = order.quantity - order.filled_quantity
            reference = (
                order.limit_price or order.stop_price or order.average_fill_price or Decimal("0")
            )
            total += remaining * reference
        return total


class ExecutionRepository(BaseRepository[Execution]):
    model = Execution

    async def list_for_order(self, order_id: uuid.UUID) -> list[Execution]:
        stmt = (
            select(Execution)
            .where(Execution.order_id == order_id)
            .order_by(Execution.executed_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
