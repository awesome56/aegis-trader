"""Simple Moving Average."""

from __future__ import annotations

from collections.abc import Sequence


def sma(values: Sequence[float], period: int) -> list[float | None]:
    """Sliding-window mean. Warm-up positions are ``None``."""
    if period <= 0:
        raise ValueError("period must be greater than 0")
    count = len(values)
    result: list[float | None] = [None] * count
    if count < period:
        return result

    window_sum = float(sum(values[:period]))
    result[period - 1] = window_sum / period
    for index in range(period, count):
        window_sum += values[index] - values[index - period]
        result[index] = window_sum / period
    return result
