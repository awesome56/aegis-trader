"""Trend Following strategy.

Rule (documented, configurable): a trend signal requires EMA structure, a
positive/negative slow-EMA slope, price on the correct side of the slow EMA, and
a minimum EMA separation. ATR provides the volatility context.

Strength = weighted normalised EMA spread and slope magnitude.
Confidence = 0.5 * fraction-of-conditions + 0.3 * regime agreement
             + 0.2 * data adequacy.
"""

from __future__ import annotations

from app.market.indicators import atr, ema, last_value
from app.models.enums import SignalDirection, StrategyType, TimeHorizon
from app.strategies.base import Strategy, clamp01
from app.strategies.enums import EvaluationStatus, StrategyKey, TrendRegime, VolatilityRegime
from app.strategies.registry import register
from app.strategies.types import StrategyContext, StrategyEvaluationResult

_BPS = 10_000.0


@register
class TrendFollowingStrategy(Strategy):
    key = StrategyKey.TREND_FOLLOWING
    name = "Trend Following"
    strategy_type = StrategyType.TREND_FOLLOWING
    time_horizon = TimeHorizon.POSITION
    description = (
        "Rides sustained directional moves using EMA fast/slow structure, slow-EMA "
        "slope and ATR-confirmed separation."
    )

    @property
    def min_candles(self) -> int:
        s = self._settings
        return max(s.STRATEGY_TREND_FAST_PERIOD, s.STRATEGY_TREND_SLOW_PERIOD) + (
            s.STRATEGY_TREND_SLOPE_LOOKBACK + 1
        )

    def evaluate(self, context: StrategyContext) -> StrategyEvaluationResult:
        settings = self._settings
        if len(context.candles) < self.min_candles:
            return self._insufficient(context)
        if context.regime.trend is TrendRegime.SIDEWAYS:
            return self._no_signal(context, "sideways regime suppresses trend following")
        if (
            context.regime.volatility is VolatilityRegime.HIGH
            and not settings.STRATEGY_TREND_ALLOW_HIGH_VOLATILITY
        ):
            return self._no_signal(context, "high volatility suppresses trend following")

        closes = [float(candle.close) for candle in context.candles]
        highs = [float(candle.high) for candle in context.candles]
        lows = [float(candle.low) for candle in context.candles]

        fast = ema(closes, settings.STRATEGY_TREND_FAST_PERIOD)
        slow = ema(closes, settings.STRATEGY_TREND_SLOW_PERIOD)
        atr_values = atr(highs, lows, closes, settings.STRATEGY_TREND_ATR_PERIOD)

        fast_now = last_value(fast)
        slow_now = last_value(slow)
        lookback = settings.STRATEGY_TREND_SLOPE_LOOKBACK
        slow_prev = slow[-1 - lookback] if len(slow) > lookback else None
        atr_now = last_value(atr_values)
        if fast_now is None or slow_now in (None, 0) or slow_prev in (None, 0):
            return self._insufficient(context)

        price = closes[-1]
        spread_bps = (fast_now - slow_now) / slow_now * _BPS
        slope_bps = (slow_now - slow_prev) / slow_prev * _BPS
        price_bps = (price - slow_now) / slow_now * _BPS
        atr_percent = (atr_now / price * 100.0) if atr_now and price else 0.0
        threshold = settings.STRATEGY_TREND_MIN_MA_SPREAD_BPS

        bullish_conditions = [
            fast_now > slow_now,
            price > slow_now,
            slope_bps > 0,
            spread_bps >= threshold,
        ]
        bearish_conditions = [
            fast_now < slow_now,
            price < slow_now,
            slope_bps < 0,
            spread_bps <= -threshold,
        ]

        if all(bullish_conditions):
            direction = SignalDirection.LONG
            conditions = bullish_conditions
        elif all(bearish_conditions):
            direction = SignalDirection.SHORT
            conditions = bearish_conditions
        else:
            return self._no_signal(context, "EMA structure/strength below threshold")

        magnitude = clamp01(abs(spread_bps) / (threshold * 3))
        slope_magnitude = clamp01(abs(slope_bps) / (threshold * 3))
        strength = 0.7 * magnitude + 0.3 * slope_magnitude

        conditions_fraction = sum(conditions) / len(conditions)
        regime_agreement = 1.0 if _trend_matches(context, direction) else 0.6
        adequacy = clamp01(len(context.candles) / (2 * self.min_candles))
        confidence = 0.5 * conditions_fraction + 0.3 * regime_agreement + 0.2 * adequacy
        if confidence < settings.STRATEGY_TREND_MIN_CONFIDENCE:
            return self._no_signal(context, "confidence below configured minimum")

        return self._result(
            context,
            EvaluationStatus.SIGNAL,
            "trend conditions satisfied",
            self._build_signal(
                context,
                direction=direction,
                strength=strength,
                confidence=confidence,
                indicators={
                    "fast_ema": round(fast_now, 6),
                    "slow_ema": round(slow_now, 6),
                    "ema_spread_bps": round(spread_bps, 4),
                    "slow_slope_bps": round(slope_bps, 4),
                    "price_vs_slow_bps": round(price_bps, 4),
                    "atr": round(atr_now, 6) if atr_now else None,
                    "atr_percent": round(atr_percent, 4),
                    "price": round(price, 6),
                },
            ),
        )


def _trend_matches(context: StrategyContext, direction: SignalDirection) -> bool:
    if direction is SignalDirection.LONG:
        return context.regime.trend is TrendRegime.BULLISH
    if direction is SignalDirection.SHORT:
        return context.regime.trend is TrendRegime.BEARISH
    return False
