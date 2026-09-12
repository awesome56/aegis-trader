"""Normalised, provider-neutral broker DTOs.

These are the only shapes the rest of the application sees from a broker. Real
broker adapters translate their payloads into these types; the paper broker
produces them directly. All money is ``Decimal``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.models.enums import OrderStatus, OrderType, PositionSide, TimeInForce, TradeSide


class BrokerStatus(StrEnum):
    """Normalised broker connectivity/health state."""

    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"
    PAPER = "PAPER"


class _Dto(BaseModel):
    model_config = ConfigDict(frozen=True)


class BrokerAccountState(_Dto):
    broker_account_id: uuid.UUID
    external_account_id: str | None = None
    provider: str
    currency: str = "USD"
    status: BrokerStatus = BrokerStatus.PAPER
    cash: Decimal
    buying_power: Decimal
    equity: Decimal
    market_value: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BrokerPosition(_Dto):
    symbol: str
    asset_id: uuid.UUID | None = None
    side: PositionSide = PositionSide.LONG
    quantity: Decimal
    average_entry_price: Decimal
    current_price: Decimal | None = None
    market_value: Decimal = Decimal("0")
    cost_basis: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    unrealized_pnl_percent: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    updated_at: datetime | None = None


class BrokerQuote(_Dto):
    symbol: str
    bid: Decimal | None = None
    ask: Decimal | None = None
    last: Decimal
    mid: Decimal | None = None
    provider: str
    market_timestamp: AwareDatetime
    received_at: AwareDatetime
    age_seconds: float = 0.0
    is_stale: bool = False

    @property
    def executable_ask(self) -> Decimal:
        return self.ask if self.ask is not None else self.last

    @property
    def executable_bid(self) -> Decimal:
        return self.bid if self.bid is not None else self.last


class BrokerOrderRequest(_Dto):
    symbol: str
    side: TradeSide
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal = Field(gt=0)
    limit_price: Decimal | None = Field(default=None, gt=0)
    stop_price: Decimal | None = Field(default=None, gt=0)
    time_in_force: TimeInForce = TimeInForce.DAY
    client_order_id: str | None = None
    idempotency_key: str | None = None
    asset_id: uuid.UUID | None = None
    portfolio_id: uuid.UUID | None = None
    metadata: dict[str, object] | None = None

    @model_validator(mode="after")
    def _validate_prices(self) -> BrokerOrderRequest:
        if self.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and self.limit_price is None:
            raise ValueError(f"{self.order_type.value} orders require a limit_price")
        if self.order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and self.stop_price is None:
            raise ValueError(f"{self.order_type.value} orders require a stop_price")
        return self

    @property
    def resolved_idempotency_key(self) -> str:
        return self.idempotency_key or self.client_order_id or uuid.uuid4().hex


class BrokerOrderResult(_Dto):
    order_id: uuid.UUID
    broker_order_id: str | None = None
    client_order_id: str | None = None
    symbol: str
    side: TradeSide
    order_type: OrderType
    time_in_force: TimeInForce
    quantity: Decimal
    filled_quantity: Decimal
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    average_fill_price: Decimal | None = None
    commission: Decimal = Decimal("0")
    status: OrderStatus
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    submitted_at: datetime | None = None
    filled_at: datetime | None = None
    cancelled_at: datetime | None = None

    @property
    def remaining_quantity(self) -> Decimal:
        return max(Decimal("0"), self.quantity - self.filled_quantity)


class Fill(_Dto):
    execution_id: uuid.UUID
    order_id: uuid.UUID
    symbol: str
    side: TradeSide
    quantity: Decimal
    price: Decimal
    gross_amount: Decimal
    commission: Decimal
    net_amount: Decimal
    executed_at: AwareDatetime


class MarketClock(_Dto):
    is_open: bool
    session: str
    current_time: AwareDatetime
    next_open: datetime | None = None
    next_close: datetime | None = None
    provider: str = "unknown"
