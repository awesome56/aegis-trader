"""Trend Following strategy tests."""

from __future__ import annotations

from app.models.enums import SignalDirection
from app.strategies.enums import EvaluationStatus
from app.strategies.registry import build
from app.strategies.trend_following import TrendFollowingStrategy

from tests.strategies.conftest import (
    context_for,
    downtrend,
    sideways,
    strategy_settings,
    uptrend,
)


def test_uptrend_produces_long_signal() -> None:
    settings = strategy_settings()
    strategy = TrendFollowingStrategy(settings)
    result = strategy.evaluate(context_for(uptrend(), settings))
    assert result.status is EvaluationStatus.SIGNAL
    assert result.signal is not None
    assert result.signal.direction is SignalDirection.LONG
    assert 0 <= result.signal.confidence <= 1
    assert 0 <= result.signal.strength <= 1
    for key in ("fast_ema", "slow_ema", "ema_spread_bps", "atr_percent"):
        assert key in result.signal.indicators


def test_downtrend_produces_short_signal() -> None:
    settings = strategy_settings()
    result = TrendFollowingStrategy(settings).evaluate(context_for(downtrend(), settings))
    assert result.status is EvaluationStatus.SIGNAL
    assert result.signal is not None
    assert result.signal.direction is SignalDirection.SHORT


def test_sideways_suppressed() -> None:
    settings = strategy_settings()
    result = TrendFollowingStrategy(settings).evaluate(context_for(sideways(), settings))
    assert result.status is EvaluationStatus.NO_SIGNAL


def test_insufficient_history() -> None:
    settings = strategy_settings()
    result = TrendFollowingStrategy(settings).evaluate(context_for(uptrend(10), settings))
    assert result.status is EvaluationStatus.INSUFFICIENT_DATA
    assert result.signal is None


def test_high_volatility_gating() -> None:
    gated = strategy_settings(
        REGIME_HIGH_VOLATILITY_ATR_PERCENT=0.3, REGIME_LOW_VOLATILITY_ATR_PERCENT=0.05
    )
    blocked = TrendFollowingStrategy(gated).evaluate(context_for(uptrend(), gated))
    assert blocked.status is EvaluationStatus.NO_SIGNAL
    assert "volatility" in blocked.reason

    allowed = strategy_settings(
        REGIME_HIGH_VOLATILITY_ATR_PERCENT=0.3,
        REGIME_LOW_VOLATILITY_ATR_PERCENT=0.05,
        STRATEGY_TREND_ALLOW_HIGH_VOLATILITY=True,
    )
    permitted = TrendFollowingStrategy(allowed).evaluate(context_for(uptrend(), allowed))
    assert permitted.status is EvaluationStatus.SIGNAL


def test_minimum_separation_threshold() -> None:
    settings = strategy_settings(STRATEGY_TREND_MIN_MA_SPREAD_BPS=100_000.0)
    result = build("trend_following", settings).evaluate(context_for(uptrend(), settings))
    assert result.status is EvaluationStatus.NO_SIGNAL
