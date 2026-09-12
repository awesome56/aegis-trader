"""Relative Strength Index (Wilder smoothing)."""

from __future__ import annotations

from collections.abc import Sequence


def rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    """Wilder RSI. Returns a measurement only — never a BUY/SELL opinion."""
    if period <= 0:
        raise ValueError("period must be greater than 0")
    count = len(values)
    result: list[float | None] = [None] * count
    if count < period + 1:
        return result

    gains = 0.0
    losses = 0.0
    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change

    average_gain = gains / period
    average_loss = losses / period
    result[period] = _rsi_from_averages(average_gain, average_loss)

    for index in range(period + 1, count):
        change = values[index] - values[index - 1]
        gain = change if change > 0 else 0.0
        loss = -change if change < 0 else 0.0
        average_gain = (average_gain * (period - 1) + gain) / period
        average_loss = (average_loss * (period - 1) + loss) / period
        result[index] = _rsi_from_averages(average_gain, average_loss)
    return result


def _rsi_from_averages(average_gain: float, average_loss: float) -> float:
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))
