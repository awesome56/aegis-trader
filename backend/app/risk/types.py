"""Typed Risk Engine contract: request, context, results, settings snapshot."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.market.domain.models import MarketQuote
from app.models.enums import RiskDecision, TimeHorizon, TradeSide, TradingState
from app.risk.enums import RiskStatus, RuleSeverity


class RiskLimitsSnapshot(BaseModel):
    """Effective limits for one evaluation (persisted settings or env defaults)."""

    model_config = ConfigDict(frozen=True)

    is_enabled: bool = True
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


class RiskRequest(BaseModel):
    """A hypothetical trade to evaluate. Never an order or a proposal."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1, max_length=32)
    side: TradeSide
    asset_id: uuid.UUID | None = None
    requested_quantity: Decimal | None = Field(default=None, gt=0)
    requested_notional: Decimal | None = Field(default=None, gt=0)
    entry_price: Decimal | None = Field(default=None, gt=0)
    stop_loss: Decimal | None = Field(default=None, gt=0)
    take_profit: Decimal | None = Field(default=None, gt=0)
    strategy_signal_id: uuid.UUID | None = None
    strategy_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    time_horizon: TimeHorizon | None = None
    source: str = "manual"
    timestamp: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict | None = None

    @model_validator(mode="after")
    def _require_size(self) -> RiskRequest:
        if self.requested_quantity is None and self.requested_notional is None:
            raise ValueError("requested_quantity or requested_notional is required")
        return self


class RuleResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    passed: bool
    severity: RuleSeverity
    message: str
    current: Decimal | None = None
    limit: Decimal | None = None
    utilization_percent: Decimal | None = None
    metadata: dict | None = None


class RiskUtilization(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    current: Decimal
    limit: Decimal
    utilization_percent: Decimal
    status: RiskStatus
    unit: str = "percent"


class PositionSizePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    requested_quantity: Decimal
    approved_quantity: Decimal
    requested_notional: Decimal
    approved_notional: Decimal
    caps: dict[str, Decimal]
    binding_constraint: str | None
    projected_exposure_percent: Decimal
    projected_position_percent: Decimal


class RiskContext(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    request: RiskRequest
    trading_state: TradingState
    limits: RiskLimitsSnapshot
    currency: str
    equity: Decimal
    cash: Decimal
    buying_power: Decimal
    portfolio_market_value: Decimal
    portfolio_exposure_percent: Decimal
    symbol_exposure_value: Decimal
    symbol_exposure_percent: Decimal
    has_existing_position: bool
    open_positions: int
    sector: str | None = None
    sector_exposure_value: Decimal = Decimal("0")
    asset_class: str | None = None
    asset_class_exposure_value: Decimal = Decimal("0")
    daily_pnl: Decimal | None = None
    drawdown_percent: Decimal = Decimal("0")
    trades_today: int = 0
    quote: MarketQuote | None = None
    quote_is_stale: bool = False
    quote_detail: str | None = None
    evaluated_at: AwareDatetime
    size_caps: dict[str, Decimal] = Field(default_factory=dict)


class RiskEvaluationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID | None = None
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
    rules: list[RuleResult]
    reasons: list[str]
    warnings: list[str]
    evaluated_at: AwareDatetime
