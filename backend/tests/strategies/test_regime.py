"""Market regime classification tests."""

from __future__ import annotations

from app.strategies.enums import TrendRegime, VolatilityRegime
from app.strategies.regime import MarketRegimeService

from tests.strategies.conftest import (
    downtrend,
    sideways,
    strategy_settings,
    uptrend,
)
from tests.strategies.helpers import build_candles


def classify(closes: list[float], **overrides: object):  # noqa: ANN202
    settings = strategy_settings(**overrides)
    service = MarketRegimeService(settings)
    return service.classify(build_candles(closes))


def test_bullish_regime() -> None:
    assessment = classify(uptrend())
    assert assessment.trend is TrendRegime.BULLISH
    assert assessment.primary.value == "BULLISH"
    assert assessment.metrics["ema_spread_bps"] > 0


def test_bearish_regime() -> None:
    assessment = classify(downtrend())
    assert assessment.trend is TrendRegime.BEARISH
    assert assessment.primary.value == "BEARISH"
    assert assessment.metrics["ema_spread_bps"] < 0


def test_sideways_regime() -> None:
    assessment = classify(sideways())
    assert assessment.trend is TrendRegime.SIDEWAYS


def test_low_volatility_primary() -> None:
    assessment = classify(sideways())
    assert assessment.volatility is VolatilityRegime.LOW
    assert assessment.primary.value == "LOW_VOLATILITY"


def test_high_volatility_primary() -> None:
    assessment = classify(
        uptrend(),
        REGIME_HIGH_VOLATILITY_ATR_PERCENT=0.3,
        REGIME_LOW_VOLATILITY_ATR_PERCENT=0.05,
    )
    assert assessment.volatility is VolatilityRegime.HIGH
    assert assessment.primary.value == "HIGH_VOLATILITY"


def test_deterministic_classification() -> None:
    service = MarketRegimeService(strategy_settings())
    candles = build_candles(uptrend())
    first = service.classify(candles)
    second = service.classify(candles)
    assert first.model_dump() == second.model_dump()


def test_insufficient_history_defaults_sideways() -> None:
    assessment = classify([100.0, 101.0, 100.5])
    assert assessment.trend is TrendRegime.SIDEWAYS
    assert "ema_spread_bps" not in assessment.metrics
