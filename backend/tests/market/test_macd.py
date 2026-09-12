"""MACD tests."""

from __future__ import annotations

import pytest
from app.market.indicators.ema import ema
from app.market.indicators.macd import macd


def test_components_are_consistent() -> None:
    values = [float(100 + (i % 7)) for i in range(60)]
    macd_line, signal_line, histogram = macd(values, 12, 26, 9)

    fast = ema(values, 12)
    slow = ema(values, 26)
    expected_macd = [
        None if (f is None or s is None) else f - s for f, s in zip(fast, slow, strict=True)
    ]
    assert macd_line == expected_macd

    for m, s, h in zip(macd_line, signal_line, histogram, strict=True):
        if m is not None and s is not None:
            assert h == pytest.approx(m - s)
        else:
            assert h is None


def test_insufficient_history_returns_none() -> None:
    macd_line, signal_line, histogram = macd([1.0, 2.0, 3.0], 12, 26, 9)
    assert macd_line == [None, None, None]
    assert signal_line == [None, None, None]
    assert histogram == [None, None, None]


def test_histogram_zero_when_flat() -> None:
    line, signal, histogram = macd([100.0] * 60, 12, 26, 9)
    assert line[-1] == pytest.approx(0.0)
    assert signal[-1] == pytest.approx(0.0)
    assert histogram[-1] == pytest.approx(0.0)


def test_fast_must_be_less_than_slow() -> None:
    with pytest.raises(ValueError):
        macd([1.0] * 30, 26, 12, 9)


def test_non_positive_periods() -> None:
    with pytest.raises(ValueError):
        macd([1.0] * 30, 0, 26, 9)
