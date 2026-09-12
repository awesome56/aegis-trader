"""Typed strategy context and results.

A ``StrategySignalResult`` is an analytical observation only: it is never an
order, a proposal, a permission to trade, or position sizing.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.market.domain.models import Candle, MarketQuote
from app.market.enums import Timeframe
from app.models.enums import MarketRegime, SignalDirection, TimeHorizon
from app.strategies.enums import EvaluationStatus, TrendRegime, VolatilityRegime


class RegimeAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    trend: TrendRegime
    volatility: VolatilityRegime
    primary: MarketRegime
    metrics: dict[str, float]
    data_timestamp: AwareDatetime


class StrategyContext(BaseModel):
    """Everything a strategy may inspect. Deliberately excludes broker/portfolio
    state — strategies must not know about cash or positions."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    symbol: str
    asset_id: uuid.UUID | None = None
    timeframe: Timeframe
    candles: list[Candle]
    quote: MarketQuote
    regime: RegimeAssessment
    evaluation_time: AwareDatetime
    data_timestamp: AwareDatetime


class StrategySignalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    asset_id: uuid.UUID | None = None
    strategy_key: str
    strategy_name: str
    timeframe: str
    direction: SignalDirection
    strength: Decimal
    confidence: Decimal
    regime: MarketRegime
    indicators: dict[str, Any]
    generated_at: AwareDatetime
    data_timestamp: AwareDatetime
    expires_at: AwareDatetime
    time_horizon: TimeHorizon = TimeHorizon.SWING


class StrategyEvaluationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy_key: str
    strategy_name: str
    symbol: str
    timeframe: str
    status: EvaluationStatus
    reason: str
    signal: StrategySignalResult | None = None
