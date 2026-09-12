"""Average True Range (Wilder smoothing)."""

from __future__ import annotations

from collections.abc import Sequence


def true_range(high: float, low: float, previous_close: float) -> float:
    return max(high - low, abs(high - previous_close), abs(low - previous_close))


def atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> list[float | None]:
    """Wilder ATR aligned with the input; warm-up positions are ``None``."""
    if period <= 0:
        raise ValueError("period must be greater than 0")
    count = len(closes)
    if not (len(highs) == len(lows) == count):
        raise ValueError("highs, lows and closes must have equal length")
    result: list[float | None] = [None] * count
    if count < period + 1:
        return result

    ranges = [true_range(highs[index], lows[index], closes[index - 1]) for index in range(1, count)]
    value = sum(ranges[:period]) / period
    result[period] = value
    for index in range(period + 1, count):
        value = (value * (period - 1) + ranges[index - 1]) / period
        result[index] = value
    return result
