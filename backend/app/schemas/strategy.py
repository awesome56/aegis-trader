"""Strategy API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MarketRegime, SignalDirection, StrategyType, TimeHorizon
from app.strategies.enums import EvaluationStatus


class _Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StrategySchema(_Schema):
    id: uuid.UUID
    key: str
    name: str
    description: str | None
    strategy_type: StrategyType
    is_enabled: bool
    timeframe: str
    priority: int
    parameters: dict | None
    asset_classes: list | None
    signal_count: int = 0
    last_signal_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SignalSchema(_Schema):
    id: uuid.UUID
    strategy_id: uuid.UUID
    strategy_key: str | None = None
    strategy_name: str | None = None
    symbol: str
    direction: SignalDirection
    strength: Decimal
    confidence: Decimal
    price: Decimal | None
    timeframe: str
    time_horizon: TimeHorizon | None
    market_regime: MarketRegime | None
    indicators: dict | None
    signal_time: datetime
    data_timestamp: datetime | None
    expires_at: datetime | None


class StrategyEvaluationSchema(_Schema):
    strategy_key: str
    strategy_name: str
    symbol: str
    timeframe: str
    status: EvaluationStatus
    reason: str
    signal: SignalEvidenceSchema | None = None


class SignalEvidenceSchema(_Schema):
    """Analytical evidence produced by an evaluation (not a persisted row)."""

    strategy_key: str
    strategy_name: str
    symbol: str
    direction: SignalDirection
    strength: Decimal
    confidence: Decimal
    price: Decimal | None = None
    timeframe: str
    time_horizon: TimeHorizon
    market_regime: MarketRegime
    indicators: dict
    generated_at: datetime
    data_timestamp: datetime
    expires_at: datetime


class SignalPageSchema(_Schema):
    items: list[SignalSchema]
    total: int
    page: int
    page_size: int


class StrategyDetailSchema(StrategySchema):
    recent_signals: list[SignalSchema] = Field(default_factory=list)


class EvaluateRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: str | None = None
    strategy_ids: list[uuid.UUID] | None = None
