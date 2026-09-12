"""Mean Reversion strategy.

Fades statistically stretched moves. A signal requires a Bollinger percent-B
extreme and (by default) an RSI extreme as confirmation, and is suppressed in
high volatility and (by default) trending regimes.

Strength = band depth / RSI extremity blend.
Confidence = 0.5 * confirmation + 0.3 * strength + 0.2 * regime fit.
"""

from __future__ import annotations

from app.market.indicators import bollinger, last_value, rsi
from app.models.enums import SignalDirection, StrategyType, TimeHorizon
from app.strategies.base import Strategy, clamp01
from app.strategies.enums import EvaluationStatus, StrategyKey, TrendRegime, VolatilityRegime
from app.strategies.registry import register
from app.strategies.types import StrategyContext, StrategyEvaluationResult


@register
class MeanReversionStrategy(Strategy):
    key = StrategyKey.MEAN_REVERSION
    name = "Mean Reversion"
    strategy_type = StrategyType.MEAN_REVERSION
    time_horizon = TimeHorizon.SWING
    description = (
        "Fades stretches beyond the Bollinger Bands, confirmed by RSI extremes, "
        "in non-trending, non-extreme-volatility regimes."
    )

    @property
    def min_candles(self) -> int:
        s = self._settings
        return max(
            s.STRATEGY_MEAN_REVERSION_BOLLINGER_PERIOD,
            s.STRATEGY_MOMENTUM_RSI_PERIOD + 1,
        )

    def evaluate(self, context: StrategyContext) -> StrategyEvaluationResult:
        settings = self._settings
        if len(context.candles) < self.min_candles:
            return self._insufficient(context)
        if context.regime.volatility is VolatilityRegime.HIGH:
            return self._no_signal(context, "high volatility suppresses mean reversion")
        if (
            context.regime.trend is not TrendRegime.SIDEWAYS
            and not settings.STRATEGY_MEAN_REVERSION_ALLOW_TRENDING
        ):
            return self._no_signal(context, "trending regime suppresses mean reversion")

        closes = [float(candle.close) for candle in context.candles]
        _, _, _, _, percent_b = bollinger(
            closes,
            settings.STRATEGY_MEAN_REVERSION_BOLLINGER_PERIOD,
            settings.STRATEGY_MEAN_REVERSION_BOLLINGER_STDDEV,
        )
        rsi_values = rsi(closes, settings.STRATEGY_MOMENTUM_RSI_PERIOD)

        percent_b_now = last_value(percent_b)
        rsi_now = last_value(rsi_values)
        if rsi_now is None:
            return self._insufficient(context)
        if percent_b_now is None:
            # Enough history but zero band width (e.g. constant prices).
            return self._no_signal(context, "zero-width Bollinger bands - no deviation")

        price = closes[-1]
        low = settings.STRATEGY_MEAN_REVERSION_PERCENT_B_LOW
        high = settings.STRATEGY_MEAN_REVERSION_PERCENT_B_HIGH
        oversold = settings.STRATEGY_RSI_OVERSOLD
        overbought = settings.STRATEGY_RSI_OVERBOUGHT
        require_confirmation = settings.STRATEGY_MEAN_REVERSION_REQUIRE_CONFIRMATION

        long_band = percent_b_now <= low
        short_band = percent_b_now >= high
        long_rsi = rsi_now <= oversold
        short_rsi = rsi_now >= overbought

        if long_band and (long_rsi or not require_confirmation):
            direction = SignalDirection.LONG
            confirmations = [long_band] + ([long_rsi] if require_confirmation else [])
            depth = clamp01((low - percent_b_now) / max(low, 1e-6))
            rsi_extremity = clamp01((oversold - rsi_now) / max(oversold, 1e-6))
        elif short_band and (short_rsi or not require_confirmation):
            direction = SignalDirection.SHORT
            confirmations = [short_band] + ([short_rsi] if require_confirmation else [])
            depth = clamp01((percent_b_now - high) / max(1.0 - high, 1e-6))
            rsi_extremity = clamp01((rsi_now - overbought) / max(100.0 - overbought, 1e-6))
        else:
            return self._no_signal(context, "price not sufficiently beyond the bands")

        strength = clamp01(0.5 + 0.5 * max(depth, rsi_extremity))
        confirmation_fraction = sum(confirmations) / len(confirmations)
        regime_fit = 1.0 if context.regime.trend is TrendRegime.SIDEWAYS else 0.7
        confidence = 0.5 * confirmation_fraction + 0.3 * strength + 0.2 * regime_fit
        if confidence < settings.STRATEGY_MEAN_REVERSION_MIN_CONFIDENCE:
            return self._no_signal(context, "confidence below configured minimum")

        return self._result(
            context,
            EvaluationStatus.SIGNAL,
            "mean-reversion conditions satisfied",
            self._build_signal(
                context,
                direction=direction,
                strength=strength,
                confidence=confidence,
                indicators={
                    "percent_b": round(percent_b_now, 4),
                    "rsi": round(rsi_now, 4),
                    "price": round(price, 6),
                    "percent_b_low": low,
                    "percent_b_high": high,
                },
            ),
        )
