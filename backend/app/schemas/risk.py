"""Risk API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskDecision, TimeHorizon, TradeSide, TradingState
from app.risk.enums import RiskStatus, RuleSeverity


class _Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RiskRequestSchema(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    side: TradeSide
    requested_quantity: Decimal | None = Field(default=None, gt=0)
    requested_notional: Decimal | None = Field(default=None, gt=0)
    entry_price: Decimal | None = Field(default=None, gt=0)
    stop_loss: Decimal | None = Field(default=None, gt=0)
    take_profit: Decimal | None = Field(default=None, gt=0)
    strategy_signal_id: uuid.UUID | None = None
    strategy_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    time_horizon: TimeHorizon | None = None


class RuleResultSchema(_Schema):
    key: str
    passed: bool
    severity: RuleSeverity
    message: str
    current: Decimal | None = None
    limit: Decimal | None = None
    utilization_percent: Decimal | None = None
    metadata: dict | None = None


class RiskEvaluationSchema(_Schema):
    id: uuid.UUID | None
    decision: RiskDecision
    symbol: str
    side: TradeSide
    source: str
    requested_quantity: Decimal
    approved_quantity: Decimal | None
    requested_notional: Decimal
    approved_notional: Decimal | None
    entry_price: Decimal | None
    stop_loss: Decimal | None
    take_profit: Decimal | None
    estimated_risk_amount: Decimal | None
    risk_reward_ratio: Decimal | None
    portfolio_exposure_before_percent: Decimal
    portfolio_exposure_after_percent: Decimal | None
    risk_score: Decimal
    rules: list[RuleResultSchema]
    reasons: list[str]
    warnings: list[str]
    evaluated_at: datetime


class RiskEvaluationPageSchema(_Schema):
    items: list[RiskEvaluationSchema]
    total: int
    page: int
    page_size: int


class RiskSettingsSchema(_Schema):
    is_enabled: bool
    max_position_percent: Decimal
    max_portfolio_exposure_percent: Decimal
    max_open_positions: int
    max_daily_loss_percent: Decimal
    max_drawdown_percent: Decimal
    max_trades_per_day: int
    max_risk_per_trade_percent: Decimal
    min_strategy_confidence: Decimal
    min_reward_risk_ratio: Decimal
    require_stop_loss: bool
    require_strategy_signal: bool
    max_sector_exposure_percent: Decimal
    max_asset_class_exposure_percent: Decimal
    unknown_sector_policy: str
    daily_loss_include_unrealized: bool
    commission_buffer_bps: Decimal


class RiskSettingsUpdateSchema(BaseModel):
    is_enabled: bool | None = None
    max_position_percent: Decimal | None = Field(default=None, gt=0, le=100)
    max_portfolio_exposure_percent: Decimal | None = Field(default=None, gt=0, le=100)
    max_open_positions: int | None = Field(default=None, gt=0)
    max_daily_loss_percent: Decimal | None = Field(default=None, gt=0, le=100)
    max_drawdown_percent: Decimal | None = Field(default=None, gt=0, le=100)
    max_trades_per_day: int | None = Field(default=None, gt=0)
    max_risk_per_trade_percent: Decimal | None = Field(default=None, gt=0, le=100)
    min_strategy_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    min_reward_risk_ratio: Decimal | None = Field(default=None, gt=0)
    require_stop_loss: bool | None = None
    require_strategy_signal: bool | None = None
    max_sector_exposure_percent: Decimal | None = Field(default=None, gt=0, le=100)
    max_asset_class_exposure_percent: Decimal | None = Field(default=None, gt=0, le=100)
    unknown_sector_policy: str | None = None
    daily_loss_include_unrealized: bool | None = None
    commission_buffer_bps: Decimal | None = Field(default=None, ge=0)


class RiskUtilizationSchema(_Schema):
    key: str
    current: Decimal
    limit: Decimal
    utilization_percent: Decimal
    status: RiskStatus
    unit: str


class RiskOverviewSchema(_Schema):
    status: RiskStatus
    trading_state: TradingState
    equity: Decimal
    cash: Decimal
    buying_power: Decimal
    portfolio_exposure_percent: Decimal
    daily_pnl: Decimal | None
    daily_loss_limit_percent: Decimal
    current_drawdown_percent: Decimal
    max_drawdown_percent: Decimal
    open_positions: int
    max_open_positions: int
    trades_today: int
    max_trades_per_day: int
    utilizations: list[RiskUtilizationSchema]
    updated_at: datetime


class TradingStatusSchema(_Schema):
    trading_state: TradingState
    previous_state: TradingState | None
    reason: str | None
    actor: str | None
    changed_at: datetime | None


class TradingActionRequest(BaseModel):
    confirm: bool = False
    reason: str | None = Field(default=None, max_length=500)


class RiskEventSchema(_Schema):
    id: uuid.UUID
    event_type: str
    severity: str
    source: str
    message: str
    actor: str | None
    payload: dict | None
    occurred_at: datetime
