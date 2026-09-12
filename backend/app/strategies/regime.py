"""Deterministic market-regime classification.

Two independent axes are produced (trend + volatility) because a single
mutually-exclusive enum makes strategy gating ambiguous. A ``primary``
``MarketRegime`` is also derived for persistence/API compatibility:

- volatility HIGH            -> primary = HIGH_VOLATILITY
- volatility LOW & sideways  -> primary = LOW_VOLATILITY
- otherwise                  -> primary = trend (BULLISH/BEARISH/SIDEWAYS)
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from app.core.config import Settings, get_settings
from app.market.domain.models import Candle
from app.market.indicators import atr, ema, last_value
from app.models.enums import MarketRegime
from app.strategies.enums import TrendRegime, VolatilityRegime
from app.strategies.types import RegimeAssessment

_BPS = 10_000.0


class MarketRegimeService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def min_candles(self) -> int:
        return self._settings.REGIME_SLOW_PERIOD + self._settings.REGIME_SLOPE_LOOKBACK + 1

    def classify(self, candles: Sequence[Candle]) -> RegimeAssessment:
        settings = self._settings
        data_timestamp = _data_timestamp(candles)
        closes = [float(candle.close) for candle in candles]
        highs = [float(candle.high) for candle in candles]
        lows = [float(candle.low) for candle in candles]

        trend = TrendRegime.SIDEWAYS
        metrics: dict[str, float] = {}
        enough = len(candles) >= self.min_candles

        if enough:
            fast = ema(closes, settings.REGIME_FAST_PERIOD)
            slow = ema(closes, settings.REGIME_SLOW_PERIOD)
            fast_now = last_value(fast)
            slow_now = last_value(slow)
            lookback = settings.REGIME_SLOPE_LOOKBACK
            slow_prev = slow[-1 - lookback] if len(slow) > lookback else None
            if fast_now is not None and slow_now not in (None, 0) and slow_prev not in (None, 0):
                spread_bps = (fast_now - slow_now) / slow_now * _BPS
                slope_bps = (slow_now - slow_prev) / slow_prev * _BPS
                price_bps = (closes[-1] - slow_now) / slow_now * _BPS
                metrics = {
                    "ema_spread_bps": round(spread_bps, 4),
                    "slow_slope_bps": round(slope_bps, 4),
                    "price_vs_slow_bps": round(price_bps, 4),
                }
                threshold = settings.REGIME_TREND_MIN_SPREAD_BPS
                if spread_bps >= threshold and slope_bps > 0 and price_bps > 0:
                    trend = TrendRegime.BULLISH
                elif spread_bps <= -threshold and slope_bps < 0 and price_bps < 0:
                    trend = TrendRegime.BEARISH
                else:
                    trend = TrendRegime.SIDEWAYS

        atr_values = atr(highs, lows, closes, settings.REGIME_ATR_PERIOD)
        atr_now = last_value(atr_values)
        close_now = closes[-1] if closes else 0.0
        atr_percent = (atr_now / close_now * 100.0) if atr_now and close_now else 0.0
        metrics["atr_percent"] = round(atr_percent, 4)

        if atr_percent >= settings.REGIME_HIGH_VOLATILITY_ATR_PERCENT:
            volatility = VolatilityRegime.HIGH
        elif atr_percent <= settings.REGIME_LOW_VOLATILITY_ATR_PERCENT:
            volatility = VolatilityRegime.LOW
        else:
            volatility = VolatilityRegime.NORMAL

        primary = _primary_regime(trend, volatility)
        return RegimeAssessment(
            trend=trend,
            volatility=volatility,
            primary=primary,
            metrics=metrics,
            data_timestamp=data_timestamp,
        )


def _primary_regime(trend: TrendRegime, volatility: VolatilityRegime) -> MarketRegime:
    if volatility is VolatilityRegime.HIGH:
        return MarketRegime.HIGH_VOLATILITY
    if volatility is VolatilityRegime.LOW and trend is TrendRegime.SIDEWAYS:
        return MarketRegime.LOW_VOLATILITY
    return {
        TrendRegime.BULLISH: MarketRegime.BULLISH,
        TrendRegime.BEARISH: MarketRegime.BEARISH,
        TrendRegime.SIDEWAYS: MarketRegime.SIDEWAYS,
    }[trend]


def _data_timestamp(candles: Sequence[Candle]) -> datetime:
    if not candles:
        return datetime.now(UTC)
    last = candles[-1]
    value = last.close_time or last.open_time
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
