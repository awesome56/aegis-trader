"""Proposal execution result types."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import OrderType, TimeHorizon, TradeSide


class ProposalCreate(BaseModel):
    """Manual TradeProposal creation payload (no execution)."""

    symbol: str = Field(min_length=1, max_length=32)
    side: TradeSide
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal | None = Field(default=None, gt=0)
    notional: Decimal | None = Field(default=None, gt=0)
    limit_price: Decimal | None = Field(default=None, gt=0)
    stop_price: Decimal | None = Field(default=None, gt=0)
    stop_loss: Decimal | None = Field(default=None, gt=0)
    take_profit: Decimal | None = Field(default=None, gt=0)
    strategy_signal_id: uuid.UUID | None = None
    time_horizon: TimeHorizon = TimeHorizon.SWING
    confidence: Decimal = Field(default=Decimal("0.5"), ge=0, le=1)
    reasoning_summary: str | None = Field(default=None, max_length=1000)
    idempotency_key: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def _validate(self) -> ProposalCreate:
        if self.quantity is None and self.notional is None:
            raise ValueError("quantity or notional is required")
        if self.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and self.limit_price is None:
            raise ValueError(f"{self.order_type.value} proposals require a limit_price")
        if self.order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and self.stop_price is None:
            raise ValueError(f"{self.order_type.value} proposals require a stop_price")
        return self


class ExecutionOutcome(BaseModel):
    """Deterministic result of an OrderManager execution attempt."""

    proposal_id: uuid.UUID
    executed: bool
    status: str
    order_id: uuid.UUID | None = None
    final_evaluation_id: uuid.UUID | None = None
    final_decision: str | None = None
    reason: str | None = None
