"""Momentum strategy tests.

RSI bounds are widened here (overbought 80 / oversold 20) so the deterministic
"choppy" datasets exercise the continuation logic rather than being filtered by
the conservative default RSI band.
"""

from __future__ import annotations

from app.models.enums import SignalDirection
from app.strategies.enums import EvaluationStatus
from app.strategies.momentum import MomentumStrategy

from tests.strategies.conftest import (
    choppy_downtrend,
    choppy_uptrend,
    context_for,
    strategy_settings,
    uptrend,
)

MOMENTUM = {"STRATEGY_RSI_OVERBOUGHT": 80.0, "STRATEGY_RSI_OVERSOLD": 20.0}


def test_bullish_momentum() -> None:
    settings = strategy_settings(**MOMENTUM)
    result = MomentumStrategy(settings).evaluate(context_for(choppy_uptrend(), settings))
    assert result.status is EvaluationStatus.SIGNAL
    assert result.signal is not None
    assert result.signal.direction is SignalDirection.LONG
    for key in ("rsi", "macd", "macd_signal", "macd_histogram", "relative_volume"):
        assert key in result.signal.indicators


def test_bearish_momentum() -> None:
    settings = strategy_settings(**MOMENTUM)
    result = MomentumStrategy(settings).evaluate(context_for(choppy_downtrend(), settings))
    assert result.status is EvaluationStatus.SIGNAL
    assert result.signal is not None
    assert result.signal.direction is SignalDirection.SHORT


def test_overextended_rsi_suppressed() -> None:
    settings = strategy_settings(**MOMENTUM)
    result = MomentumStrategy(settings).evaluate(context_for(uptrend(), settings))
    assert result.status is EvaluationStatus.NO_SIGNAL
    assert "overbought" in result.reason


def test_weak_volume_suppressed() -> None:
    settings = strategy_settings(**MOMENTUM, STRATEGY_MOMENTUM_MIN_RELATIVE_VOLUME=5.0)
    result = MomentumStrategy(settings).evaluate(context_for(choppy_uptrend(), settings))
    assert result.status is EvaluationStatus.NO_SIGNAL


def test_insufficient_history() -> None:
    settings = strategy_settings(**MOMENTUM)
    result = MomentumStrategy(settings).evaluate(context_for(choppy_uptrend()[:10], settings))
    assert result.status is EvaluationStatus.INSUFFICIENT_DATA
