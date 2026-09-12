"""TradeProposal API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AssetClass,
    OrderAction,
    OrderType,
    ProposalSource,
    ProposalStatus,
    TimeHorizon,
)
from app.proposals.types import ProposalCreate
from app.schemas.broker import BrokerOrderSchema
from app.schemas.risk import RiskEvaluationSchema


class _Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProposalCreateRequest(ProposalCreate):
    """Alias: manual proposals are the only V1 creation path."""


class ProposalSchema(_Schema):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    strategy_id: uuid.UUID | None = None
    strategy_signal_id: uuid.UUID | None = None
    symbol: str
    asset_class: AssetClass
    action: OrderAction
    order_type: OrderType
    source: ProposalSource
    status: ProposalStatus
    proposed_quantity: Decimal
    proposed_position_percentage: Decimal | None = None
    requested_notional: Decimal | None = None
    entry_price: Decimal | None = None
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    confidence: Decimal
    time_horizon: TimeHorizon
    reasoning_summary: str | None = None
    market_regime: str | None = None
    failure_reason: str | None = None
    expires_at: datetime | None = None
    decided_at: datetime | None = None
    executed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ExecutionSchema(_Schema):
    id: uuid.UUID
    order_id: uuid.UUID
    quantity: Decimal
    price: Decimal
    gross_amount: Decimal | None = None
    net_amount: Decimal | None = None
    fees: Decimal
    commission: Decimal
    slippage: Decimal
    liquidity: str | None = None
    executed_at: datetime


class ProposalDetailSchema(BaseModel):
    proposal: ProposalSchema
    evaluations: list[RiskEvaluationSchema] = Field(default_factory=list)
    orders: list[BrokerOrderSchema] = Field(default_factory=list)
    executions: list[ExecutionSchema] = Field(default_factory=list)


class ProposalEvaluationResponse(BaseModel):
    proposal: ProposalSchema
    evaluation: RiskEvaluationSchema


class ProposalPageSchema(BaseModel):
    items: list[ProposalSchema]
    total: int
    limit: int
    offset: int
