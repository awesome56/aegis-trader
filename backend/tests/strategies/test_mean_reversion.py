"""Mean Reversion strategy tests.

The trend-separation threshold is raised so the synthetic spike datasets classify
as SIDEWAYS rather than trending, isolating the mean-reversion rule itself.
"""

from __future__ import annotations

from app.models.enums import SignalDirection
from app.strategies.enums import EvaluationStatus
from app.strategies.mean_reversion import MeanReversionStrategy

from tests.strategies.conftest import (
    context_for,
    inside_bands,
    spike_down,
    spike_up,
    strategy_settings,
)

SIDEWAYS = {"REGIME_TREND_MIN_SPREAD_BPS": 500.0}


def test_below_lower_band_is_long() -> None:
    settings = strategy_settings(**SIDEWAYS)
    result = MeanReversionStrategy(settings).evaluate(context_for(spike_down(), settings))
    assert result.status is EvaluationStatus.SIGNAL
    assert result.signal is not None
    assert result.signal.direction is SignalDirection.LONG
    assert result.signal.indicators["percent_b"] <= 0.05


def test_above_upper_band_is_short() -> None:
    settings = strategy_settings(**SIDEWAYS)
    result = MeanReversionStrategy(settings).evaluate(context_for(spike_up(), settings))
    assert result.status is EvaluationStatus.SIGNAL
    assert result.signal is not None
    assert result.signal.direction is SignalDirection.SHORT


def test_inside_bands_no_signal() -> None:
    settings = strategy_settings(**SIDEWAYS)
    result = MeanReversionStrategy(settings).evaluate(context_for(inside_bands(), settings))
    assert result.status is EvaluationStatus.NO_SIGNAL


def test_constant_prices_no_signal() -> None:
    settings = strategy_settings(**SIDEWAYS)
    result = MeanReversionStrategy(settings).evaluate(context_for([100.0] * 40, settings))
    assert result.status is EvaluationStatus.NO_SIGNAL
    assert "zero-width" in result.reason


def test_high_volatility_suppressed() -> None:
    settings = strategy_settings(
        **SIDEWAYS,
        REGIME_HIGH_VOLATILITY_ATR_PERCENT=0.3,
        REGIME_LOW_VOLATILITY_ATR_PERCENT=0.05,
    )
    result = MeanReversionStrategy(settings).evaluate(context_for(spike_down(), settings))
    assert result.status is EvaluationStatus.NO_SIGNAL
    assert "volatility" in result.reason


def test_trending_suppressed_by_default() -> None:
    settings = strategy_settings()  # default trend threshold: spike is trending
    result = MeanReversionStrategy(settings).evaluate(context_for(spike_down(), settings))
    assert result.status is EvaluationStatus.NO_SIGNAL
    assert "trending" in result.reason


def test_insufficient_history() -> None:
    settings = strategy_settings(**SIDEWAYS)
    result = MeanReversionStrategy(settings).evaluate(context_for(spike_down()[:5], settings))
    assert result.status is EvaluationStatus.INSUFFICIENT_DATA
