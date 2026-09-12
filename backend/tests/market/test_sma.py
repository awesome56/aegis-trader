"""SMA tests with manually verified values."""

from __future__ import annotations

import pytest
from app.market.indicators.sma import sma


def test_known_values() -> None:
    assert sma([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]


def test_period_one_is_identity() -> None:
    assert sma([1.0, 2.0, 3.0], 1) == [1.0, 2.0, 3.0]


def test_insufficient_history_returns_none() -> None:
    assert sma([1, 2], 5) == [None, None]


def test_empty_input() -> None:
    assert sma([], 3) == []


def test_constant_prices() -> None:
    assert sma([10.0] * 5, 2) == [None, 10.0, 10.0, 10.0, 10.0]


def test_invalid_period() -> None:
    with pytest.raises(ValueError):
        sma([1, 2, 3], 0)
