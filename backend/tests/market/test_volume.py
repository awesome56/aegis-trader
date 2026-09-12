"""Volume analysis tests."""

from __future__ import annotations

import pytest
from app.market.indicators.volume import volume_analysis


def test_known_values() -> None:
    stats = volume_analysis([100, 200], 2)
    assert stats.moving_average == [None, 150.0]
    assert stats.current_volume == 200.0
    assert stats.average_volume == 150.0
    assert stats.relative_volume == pytest.approx(200 / 150)
    assert stats.volume_change_pct == pytest.approx(100.0)


def test_constant_volume() -> None:
    stats = volume_analysis([500] * 10, 3)
    assert stats.relative_volume == pytest.approx(1.0)
    assert stats.volume_change_pct == pytest.approx(0.0)


def test_empty_input() -> None:
    stats = volume_analysis([], 5)
    assert stats.current_volume is None
    assert stats.moving_average == []


def test_zero_volume_does_not_divide_by_zero() -> None:
    stats = volume_analysis([0, 0, 0], 3)
    assert stats.average_volume == 0.0
    assert stats.relative_volume is None
    # Change vs a zero prior bar is undefined, not zero.
    assert stats.volume_change_pct is None


def test_invalid_period() -> None:
    with pytest.raises(ValueError):
        volume_analysis([1, 2, 3], 0)
