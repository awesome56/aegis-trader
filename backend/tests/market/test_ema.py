"""EMA tests with manually verified values."""

from __future__ import annotations

import pytest
from app.market.indicators.ema import ema


def test_known_sequence() -> None:
    # seed = SMA(1,2,3)=2 ; k=0.5 -> 4*0.5+2*0.5=3 ; 5*0.5+3*0.5=4
    assert ema([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]


def test_constant_prices_stay_constant() -> None:
    assert ema([7.0] * 6, 3) == [None, None, 7.0, 7.0, 7.0, 7.0]


def test_insufficient_history_returns_none() -> None:
    assert ema([1, 2, 3], 5) == [None, None, None]


def test_invalid_period() -> None:
    with pytest.raises(ValueError):
        ema([1, 2, 3], -1)
