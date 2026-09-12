"""Exponential Moving Average (standard smoothing, SMA-seeded)."""

from __future__ import annotations

from collections.abc import Sequence


def ema(values: Sequence[float], period: int) -> list[float | None]:
    """EMA with smoothing ``k = 2 / (period + 1)``.

    The first value is seeded with the SMA of the first ``period`` observations,
    which is the conventional initialisation. Warm-up positions are ``None``.
    """
    if period <= 0:
        raise ValueError("period must be greater than 0")
    count = len(values)
    result: list[float | None] = [None] * count
    if count < period:
        return result

    smoothing = 2 / (period + 1)
    previous = float(sum(values[:period])) / period
    result[period - 1] = previous
    for index in range(period, count):
        previous = values[index] * smoothing + previous * (1 - smoothing)
        result[index] = previous
    return result
