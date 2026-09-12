"""RSI tests (Wilder smoothing)."""

from __future__ import annotations

import pytest
from app.market.indicators.rsi import rsi


def test_known_sequence_period_two() -> None:
    # changes: +1,+1,-1,+1 -> 100, 50, 75
    assert rsi([10, 11, 12, 11, 12], 2) == [None, None, 100.0, 50.0, 75.0]


def test_monotonic_rise_saturates_at_100() -> None:
    values = [float(i) for i in range(1, 20)]
    result = rsi(values, 14)
    assert result[-1] == 100.0


def test_monotonic_fall_bottoms_at_0() -> None:
    values = [float(i) for i in range(20, 1, -1)]
    result = rsi(values, 14)
    assert result[-1] == 0.0


def test_constant_prices_are_neutral() -> None:
    assert rsi([50.0] * 20, 14)[-1] == 50.0


def test_insufficient_history() -> None:
    assert rsi([1, 2, 3], 14) == [None, None, None]


def test_bounds() -> None:
    values = [100, 102, 101, 105, 104, 108, 107, 110, 109, 112, 111, 115, 113, 118, 117, 120]
    for value in rsi(values, 14):
        if value is not None:
            assert 0 <= value <= 100


def test_invalid_period() -> None:
    with pytest.raises(ValueError):
        rsi([1, 2, 3], 0)
