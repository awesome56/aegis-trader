"""Strategy interface and shared helpers.

Strategies are pure: they evaluate already-loaded candles/quote and never touch
the database, brokers, portfolio, or other IO. IO belongs to the
``StrategyService``. Confidence and strength are deterministic functions of the
measurements (documented per strategy); no randomness and no LLM.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.core.config import Settings, get_settings
from app.market.enums import Timeframe
from app.models.enums import MarketRegime, SignalDirection, StrategyType, TimeHorizon
from app.strategies.enums import EvaluationStatus, StrategyKey
from app.strategies.types import (
    StrategyContext,
    StrategyEvaluationResult,
    StrategySignalResult,
)


def dec(value: float | int | Decimal) -> Decimal:
    """Normalise a measurement to a 6-dp Decimal (never from a float literal)."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(round(float(value), 6)))


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


class Strategy(ABC):
    key: StrategyKey
    name: str
    strategy_type: StrategyType
    description: str = ""
    time_horizon: TimeHorizon = TimeHorizon.SWING

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    @abstractmethod
    def min_candles(self) -> int:
        """Minimum candles required for a full evaluation."""

    @abstractmethod
    def evaluate(self, context: StrategyContext) -> StrategyEvaluationResult:
        """Evaluate loaded data and return a typed result. No IO."""

    # --- result helpers -----------------------------------------------------
    def _result(
        self,
        context: StrategyContext,
        status: EvaluationStatus,
        reason: str,
        signal: StrategySignalResult | None = None,
    ) -> StrategyEvaluationResult:
        return StrategyEvaluationResult(
            strategy_key=self.key.value,
            strategy_name=self.name,
            symbol=context.symbol,
            timeframe=context.timeframe.value,
            status=status,
            reason=reason,
            signal=signal,
        )

    def _insufficient(self, context: StrategyContext) -> StrategyEvaluationResult:
        return self._result(
            context,
            EvaluationStatus.INSUFFICIENT_DATA,
            f"requires at least {self.min_candles} candles",
        )

    def _no_signal(self, context: StrategyContext, reason: str) -> StrategyEvaluationResult:
        return self._result(context, EvaluationStatus.NO_SIGNAL, reason)

    def _build_signal(
        self,
        context: StrategyContext,
        *,
        direction: SignalDirection,
        strength: float,
        confidence: float,
        indicators: dict[str, Any],
    ) -> StrategySignalResult:
        ttl = self._settings.STRATEGY_SIGNAL_TTL_MULTIPLIER
        expires_at: datetime = context.data_timestamp + context.timeframe.duration * ttl
        return StrategySignalResult(
            symbol=context.symbol,
            asset_id=context.asset_id,
            strategy_key=self.key.value,
            strategy_name=self.name,
            timeframe=context.timeframe.value,
            direction=direction,
            strength=dec(clamp01(strength)),
            confidence=dec(clamp01(confidence)),
            regime=context.regime.primary,
            indicators=indicators,
            generated_at=context.evaluation_time,
            data_timestamp=context.data_timestamp,
            expires_at=expires_at,
            time_horizon=self.time_horizon,
        )


def timeframe_regimes() -> tuple[MarketRegime, ...]:
    """Convenience for strategy gating tests."""
    return (MarketRegime.BULLISH, MarketRegime.BEARISH, MarketRegime.SIDEWAYS)


def default_timeframe(settings: Settings | None = None) -> Timeframe:
    settings = settings or get_settings()
    return Timeframe.parse(settings.STRATEGY_DEFAULT_TIMEFRAME)
