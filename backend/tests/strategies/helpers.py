"""Helpers for building deterministic synthetic candles/contexts in tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.market.domain.models import Candle, MarketQuote
from app.market.enums import Timeframe
from app.strategies.regime import MarketRegimeService
from app.strategies.types import RegimeAssessment, StrategyContext

FIXED_NOW = datetime(2026, 1, 15, 15, 0, 0, tzinfo=UTC)


def build_candles(
    closes: list[float],
    *,
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    volumes: list[int] | None = None,
    timeframe: Timeframe = Timeframe.ONE_HOUR,
    end: datetime = FIXED_NOW,
) -> list[Candle]:
    count = len(closes)
    volumes = volumes or [1_000_000] * count
    candles: list[Candle] = []
    for index, close in enumerate(closes):
        open_time = end - timeframe.duration * (count - index)
        open_price = closes[index - 1] if index > 0 else close
        high_price = highs[index] if highs else max(open_price, close) * 1.001
        low_price = lows[index] if lows else min(open_price, close) * 0.999
        high = max(high_price, open_price, close)
        low = min(low_price, open_price, close)
        candles.append(
            Candle(
                symbol="TEST",
                timeframe=timeframe,
                open_time=open_time,
                close_time=open_time + timeframe.duration,
                open=Decimal(str(round(open_price, 4))),
                high=Decimal(str(round(high, 4))),
                low=Decimal(str(round(low, 4))),
                close=Decimal(str(round(close, 4))),
                volume=volumes[index],
                provider="test",
            )
        )
    return candles


def build_quote(price: float, *, timestamp: datetime = FIXED_NOW) -> MarketQuote:
    return MarketQuote(
        symbol="TEST",
        bid=Decimal(str(round(price * 0.9999, 4))),
        ask=Decimal(str(round(price * 1.0001, 4))),
        last=Decimal(str(round(price, 4))),
        provider="test",
        market_timestamp=timestamp,
        received_at=timestamp,
    )


def build_context(
    closes: list[float],
    regime_service: MarketRegimeService,
    *,
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    volumes: list[int] | None = None,
    timeframe: Timeframe = Timeframe.ONE_HOUR,
    end: datetime = FIXED_NOW,
) -> StrategyContext:
    candles = build_candles(
        closes, highs=highs, lows=lows, volumes=volumes, timeframe=timeframe, end=end
    )
    assessment: RegimeAssessment = regime_service.classify(candles)
    data_timestamp = candles[-1].open_time
    return StrategyContext(
        symbol="TEST",
        asset_id=None,
        timeframe=timeframe,
        candles=candles,
        quote=build_quote(closes[-1], timestamp=end),
        regime=assessment,
        evaluation_time=end,
        data_timestamp=data_timestamp,
    )
