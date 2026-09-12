"""Broker API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OrderStatus, OrderType, TimeInForce, TradeSide


class _Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BrokerAccountSchema(_Schema):
    broker_account_id: uuid.UUID
    external_account_id: str | None
    provider: str
    currency: str
    status: str
    cash: Decimal
    buying_power: Decimal
    equity: Decimal
    market_value: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    created_at: datetime | None
    updated_at: datetime | None


class BrokerPositionSchema(_Schema):
    symbol: str
    asset_id: uuid.UUID | None
    side: str
    quantity: Decimal
    average_entry_price: Decimal
    current_price: Decimal | None
    market_value: Decimal
    cost_basis: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    realized_pnl: Decimal
    updated_at: datetime | None


class BrokerOrderSchema(_Schema):
    order_id: uuid.UUID
    broker_order_id: str | None
    client_order_id: str | None
    symbol: str
    side: TradeSide
    order_type: OrderType
    time_in_force: TimeInForce
    quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    limit_price: Decimal | None
    stop_price: Decimal | None
    average_fill_price: Decimal | None
    commission: Decimal
    status: OrderStatus
    error_message: str | None
    created_at: datetime | None
    updated_at: datetime | None
    submitted_at: datetime | None
    filled_at: datetime | None
    cancelled_at: datetime | None

    @classmethod
    def from_result(cls, result) -> BrokerOrderSchema:  # noqa: ANN001
        return cls(
            **result.model_dump(),
            remaining_quantity=result.remaining_quantity,
        )

    @classmethod
    def from_model(cls, order) -> BrokerOrderSchema:  # noqa: ANN001
        return cls(
            order_id=order.id,
            broker_order_id=order.broker_order_id,
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            time_in_force=order.time_in_force,
            quantity=order.quantity,
            filled_quantity=order.filled_quantity,
            remaining_quantity=max(Decimal("0"), order.quantity - order.filled_quantity),
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            average_fill_price=order.average_fill_price,
            commission=order.fees,
            status=order.status,
            error_message=order.error_message,
            created_at=order.created_at,
            updated_at=order.updated_at,
            submitted_at=order.submitted_at,
            filled_at=order.filled_at,
            cancelled_at=order.cancelled_at,
        )


class BrokerQuoteSchema(_Schema):
    symbol: str
    bid: Decimal | None
    ask: Decimal | None
    last: Decimal
    mid: Decimal | None
    provider: str
    market_timestamp: datetime
    received_at: datetime
    age_seconds: float
    is_stale: bool


class MarketClockSchema(_Schema):
    is_open: bool
    session: str
    current_time: datetime
    next_open: datetime | None
    next_close: datetime | None
    provider: str


class OrderCreateRequest(BaseModel):
    """Manual paper-order submission payload (paper mode only)."""

    symbol: str = Field(min_length=1, max_length=32)
    side: TradeSide
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal = Field(gt=0)
    limit_price: Decimal | None = Field(default=None, gt=0)
    stop_price: Decimal | None = Field(default=None, gt=0)
    time_in_force: TimeInForce = TimeInForce.DAY
    client_order_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=128)


class BrokerOrderListSchema(_Schema):
    items: list[BrokerOrderSchema]
    total: int
