"""Bollinger Bands."""

from __future__ import annotations

from collections.abc import Sequence

from app.market.indicators.base import population_std
from app.market.indicators.sma import sma


def bollinger(
    values: Sequence[float],
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
    list[float | None],
]:
    """Return ``(middle, upper, lower, bandwidth, percent_b)``.

    Standard deviation is the population deviation over the window (conventional
    for Bollinger Bands). ``percent_b = (price - lower) / (upper - lower)``.
    """
    if period <= 0:
        raise ValueError("period must be greater than 0")
    if num_std <= 0:
        raise ValueError("num_std must be greater than 0")

    count = len(values)
    middle = sma(values, period)
    upper: list[float | None] = [None] * count
    lower: list[float | None] = [None] * count
    bandwidth: list[float | None] = [None] * count
    percent_b: list[float | None] = [None] * count

    for index in range(period - 1, count):
        window = list(values[index - period + 1 : index + 1])
        mean = middle[index]
        assert mean is not None
        deviation = population_std(window, mean)
        upper_value = mean + num_std * deviation
        lower_value = mean - num_std * deviation
        upper[index] = upper_value
        lower[index] = lower_value
        bandwidth[index] = (upper_value - lower_value) / mean if mean else None
        span = upper_value - lower_value
        percent_b[index] = (values[index] - lower_value) / span if span else None
    return middle, upper, lower, bandwidth, percent_b
