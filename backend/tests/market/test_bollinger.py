"""Bollinger Bands tests."""

from __future__ import annotations

import math

import pytest
from app.market.indicators.bollinger import bollinger


def test_known_values() -> None:
    middle, upper, lower, bandwidth, percent_b = bollinger([1.0, 2.0, 3.0], 3, 2.0)
    assert middle[-1] == pytest.approx(2.0)
    deviation = math.sqrt(2 / 3)
    assert upper[-1] == pytest.approx(2.0 + 2 * deviation)
    assert lower[-1] == pytest.approx(2.0 - 2 * deviation)
    assert bandwidth[-1] == pytest.approx((4 * deviation) / 2.0)
    assert percent_b[-1] == pytest.approx((3.0 - lower[-1]) / (upper[-1] - lower[-1]))


def test_constant_prices_collapse_bands() -> None:
    middle, upper, lower, bandwidth, percent_b = bollinger([5.0] * 5, 3, 2.0)
    assert middle[-1] == 5.0
    assert upper[-1] == 5.0
    assert lower[-1] == 5.0
    assert bandwidth[-1] == 0.0
    assert percent_b[-1] is None


def test_insufficient_history() -> None:
    middle, upper, _, _, _ = bollinger([1.0, 2.0], 5, 2.0)
    assert middle == [None, None]
    assert upper == [None, None]


def test_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        bollinger([1.0, 2.0, 3.0], 0)
    with pytest.raises(ValueError):
        bollinger([1.0, 2.0, 3.0], 3, 0)
