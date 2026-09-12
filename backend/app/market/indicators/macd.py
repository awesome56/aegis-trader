"""MACD (Moving Average Convergence Divergence)."""

from __future__ import annotations

from collections.abc import Sequence

from app.market.indicators.ema import ema


def macd(
    values: Sequence[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Return ``(macd_line, signal_line, histogram)`` aligned with the input.

    ``signal`` is the EMA of the non-warm-up MACD line.
    """
    if fast_period <= 0 or slow_period <= 0 or signal_period <= 0:
        raise ValueError("MACD periods must be greater than 0")
    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")

    count = len(values)
    fast = ema(values, fast_period)
    slow = ema(values, slow_period)

    macd_line: list[float | None] = [
        None if (f is None or s is None) else f - s for f, s in zip(fast, slow, strict=True)
    ]

    first = next((index for index, value in enumerate(macd_line) if value is not None), None)
    signal_line: list[float | None] = [None] * count
    if first is not None:
        signal_series = ema(
            [value for value in macd_line[first:] if value is not None], signal_period
        )
        for offset, value in enumerate(signal_series):
            signal_line[first + offset] = value

    histogram: list[float | None] = [
        None if (m is None or s is None) else m - s
        for m, s in zip(macd_line, signal_line, strict=True)
    ]
    return macd_line, signal_line, histogram
