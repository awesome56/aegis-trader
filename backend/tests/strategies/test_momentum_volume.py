"""Momentum must not fabricate volume (notably for spot FX)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.market.domain.models import Candle, MarketQuote
from app.market.enums import Timeframe
from app.market.providers import scenarios
from app.strategies.enums import EvaluationStatus, TrendRegime, VolatilityRegime
from app.strategies.regime import MarketRegimeService
from app.strategies.registry import build
from app.strategies.types import RegimeAssessment, StrategyContext

from tests.strategies.conftest import strategy_settings

NOW = datetime(2026, 1, 15, 15, 0, tzinfo=UTC)
TF = Timeframe.ONE_HOUR


def _candles(volume: int) -> list[Candle]:
    closes = scenarios.scenario_closes("momentum_bullish", 66, 100.0)
    env = scenarios.envelope("momentum_bullish")
    out: list[Candle] = []
    for index, close in enumerate(closes):
        opened = NOW - timedelta(hours=65 - index)
        open_price = closes[index - 1] if index > 0 else close * (1 - env)
        out.append(
            Candle(
                symbol="EUR/USD",
                timeframe=TF,
                open_time=opened,
                close_time=opened + TF.duration,
                open=Decimal(str(open_price)),
                high=Decimal(str(max(open_price, close) * (1 + env))),
                low=Decimal(str(min(open_price, close) * (1 - env))),
                close=Decimal(str(close)),
                volume=volume,
                provider="test",
            )
        )
    return out


def _context(candles: list[Candle]) -> StrategyContext:
    regime = RegimeAssessment(
        trend=TrendRegime.BULLISH,
        volatility=VolatilityRegime.NORMAL,
        primary=__import__("app.models.enums", fromlist=["MarketRegime"]).MarketRegime.BULLISH,
        metrics={},
        data_timestamp=NOW,
    )
    last = candles[-1]
    return StrategyContext(
        symbol=last.symbol,
        timeframe=TF,
        candles=candles,
        quote=MarketQuote(
            symbol=last.symbol,
            last=last.close,
            provider="test",
            market_timestamp=NOW,
            received_at=NOW,
        ),
        regime=regime,
        evaluation_time=NOW,
        data_timestamp=NOW,
    )


def test_momentum_suppressed_without_volume() -> None:
    settings = strategy_settings()
    outcome = build("momentum", settings).evaluate(_context(_candles(0)))
    assert outcome.status is EvaluationStatus.NO_SIGNAL
    assert "volume" in outcome.reason.lower()
    assert outcome.signal is None


def test_market_regime_service_still_used_elsewhere() -> None:
    settings = strategy_settings()
    assert MarketRegimeService(settings).min_candles > 0
