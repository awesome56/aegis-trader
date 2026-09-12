"""ATR tests (Wilder smoothing)."""

from __future__ import annotations

import pytest
from app.market.indicators.atr import atr, true_range


def test_true_range() -> None:
    assert true_range(high=11.5, low=10.5, previous_close=10.0) == 1.5
    assert true_range(high=11.0, low=10.0, previous_close=12.0) == 2.0


def test_known_atr_period_two() -> None:
    highs = [10.5, 11.5, 12.5]
    lows = [9.5, 10.5, 11.5]
    closes = [10.0, 11.0, 12.0]
    # TR1 = 1.5, TR2 = 1.5 -> ATR at index 2 = 1.5
    assert atr(highs, lows, closes, 2) == [None, None, 1.5]


def test_constant_range() -> None:
    highs = [11.0] * 10
    lows = [9.0] * 10
    closes = [10.0] * 10
    result = atr(highs, lows, closes, 3)
    assert result[-1] == pytest.approx(2.0)


def test_insufficient_history() -> None:
    assert atr([1.0], [0.5], [0.8], 14) == [None]


def test_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        atr([1.0, 2.0], [1.0], [1.0, 1.0], 2)


def test_invalid_period() -> None:
    with pytest.raises(ValueError):
        atr([1.0], [0.5], [0.8], 0)
