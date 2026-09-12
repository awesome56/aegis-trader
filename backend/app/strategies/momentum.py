"""Momentum strategy.

Continuation, not blind inversion: bullish momentum needs MACD above its signal
with a positive histogram, RSI in a positive-but-not-overbought band, and volume
confirmation. Overextended RSI suppresses the signal rather than triggering a
reversal.

Strength = normalised MACD histogram relative to price.
Confidence = 0.6 * conditions + 0.25 * volume confirmation + 0.15 * adequacy.
"""

from __future__ import annotations

from app.market.indicators import last_value, macd, rsi
from app.market.indicators.volume import volume_analysis
from app.models.enums import SignalDirection, StrategyType, TimeHorizon
from app.strategies.base import Strategy, clamp01
from app.strategies.enums import EvaluationStatus, StrategyKey, TrendRegime, VolatilityRegime
from app.strategies.registry import register
from app.strategies.types import StrategyContext, StrategyEvaluationResult

_STRENGTH_REFERENCE = 0.005  # 0.5% of price for a full-strength histogram


@register
class MomentumStrategy(Strategy):
    key = StrategyKey.MOMENTUM
    name = "Momentum"
    strategy_type = StrategyType.MOMENTUM
    time_horizon = TimeHorizon.SWING
    description = (
        "Buys strength confirmed by MACD, a positive-but-not-overbought RSI band "
        "and relative-volume expansion."
    )

    @property
    def min_candles(self) -> int:
        s = self._settings
        return (
            max(
                s.STRATEGY_MOMENTUM_MACD_SLOW_PERIOD + s.STRATEGY_MOMENTUM_MACD_SIGNAL_PERIOD + 1,
                s.STRATEGY_MOMENTUM_RSI_PERIOD + 1,
                s.STRATEGY_MOMENTUM_VOLUME_PERIOD,
            )
            + 2
        )

    def evaluate(self, context: StrategyContext) -> StrategyEvaluationResult:
        settings = self._settings
        if len(context.candles) < self.min_candles:
            return self._insufficient(context)
        if context.regime.trend is TrendRegime.SIDEWAYS:
            return self._no_signal(context, "no directional regime for momentum")
        if (
            context.regime.volatility is VolatilityRegime.HIGH
            and not settings.STRATEGY_MOMENTUM_ALLOW_HIGH_VOLATILITY
        ):
            return self._no_signal(context, "high volatility suppresses momentum")

        closes = [float(candle.close) for candle in context.candles]
        volumes = [int(candle.volume or 0) for candle in context.candles]

        rsi_values = rsi(closes, settings.STRATEGY_MOMENTUM_RSI_PERIOD)
        macd_line, signal_line, histogram = macd(
            closes,
            settings.STRATEGY_MOMENTUM_MACD_FAST_PERIOD,
            settings.STRATEGY_MOMENTUM_MACD_SLOW_PERIOD,
            settings.STRATEGY_MOMENTUM_MACD_SIGNAL_PERIOD,
        )
        volume_stats = volume_analysis(volumes, settings.STRATEGY_MOMENTUM_VOLUME_PERIOD)

        rsi_now = last_value(rsi_values)
        macd_now = last_value(macd_line)
        signal_now = last_value(signal_line)
        hist_now = last_value(histogram)
        relative_volume = volume_stats.relative_volume
        if None in (rsi_now, macd_now, signal_now, hist_now):
            return self._insufficient(context)

        assert rsi_now is not None and macd_now is not None
        assert signal_now is not None and hist_now is not None
        price = closes[-1]
        oversold = settings.STRATEGY_RSI_OVERSOLD
        overbought = settings.STRATEGY_RSI_OVERBOUGHT
        min_relative_volume = settings.STRATEGY_MOMENTUM_MIN_RELATIVE_VOLUME
        volume_confirms = relative_volume is not None and relative_volume >= min_relative_volume

        if rsi_now >= overbought:
            return self._no_signal(context, "RSI overbought - momentum exhausted")
        if rsi_now <= oversold:
            return self._no_signal(context, "RSI oversold - downward momentum exhausted")

        bullish = [
            macd_now > signal_now,
            hist_now > 0,
            50.0 < rsi_now < overbought,
            volume_confirms,
        ]
        bearish = [macd_now < signal_now, hist_now < 0, oversold < rsi_now < 50.0, volume_confirms]

        if all(bullish):
            direction = SignalDirection.LONG
            conditions = bullish
        elif all(bearish):
            direction = SignalDirection.SHORT
            conditions = bearish
        else:
            return self._no_signal(context, "MACD/RSI/volume conditions not aligned")

        strength = clamp01(abs(hist_now) / (price * _STRENGTH_REFERENCE)) if price else 0.0
        conditions_fraction = sum(conditions) / len(conditions)
        volume_factor = (
            clamp01(relative_volume / (min_relative_volume * 1.5))
            if relative_volume is not None and min_relative_volume > 0
            else 0.5
        )
        adequacy = clamp01(len(context.candles) / (2 * self.min_candles))
        confidence = 0.6 * conditions_fraction + 0.25 * volume_factor + 0.15 * adequacy
        if confidence < settings.STRATEGY_MOMENTUM_MIN_CONFIDENCE:
            return self._no_signal(context, "confidence below configured minimum")

        return self._result(
            context,
            EvaluationStatus.SIGNAL,
            "momentum conditions satisfied",
            self._build_signal(
                context,
                direction=direction,
                strength=strength,
                confidence=confidence,
                indicators={
                    "rsi": round(rsi_now, 4),
                    "macd": round(macd_now, 6),
                    "macd_signal": round(signal_now, 6),
                    "macd_histogram": round(hist_now, 6),
                    "relative_volume": round(relative_volume, 4)
                    if relative_volume is not None
                    else None,
                    "average_volume": round(volume_stats.average_volume, 2)
                    if volume_stats.average_volume is not None
                    else None,
                    "price": round(price, 6),
                },
            ),
        )
