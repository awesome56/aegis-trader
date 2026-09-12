"""Volume analysis (deterministic quantitative measures only)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple

from app.market.indicators.sma import sma


class VolumeStats(NamedTuple):
    current_volume: float | None
    average_volume: float | None
    relative_volume: float | None
    volume_change_pct: float | None
    moving_average: list[float | None]


def volume_analysis(volumes: Sequence[int], period: int = 20) -> VolumeStats:
    """Volume measurements over the provided window.

    ``relative_volume`` = current / moving average; ``volume_change_pct`` is the
    change versus the previous bar. No sentiment scores are produced.
    """
    if period <= 0:
        raise ValueError("period must be greater than 0")
    if not volumes:
        return VolumeStats(None, None, None, None, [])

    numeric = [float(volume) for volume in volumes]
    moving_average = sma(numeric, period)
    average = next((value for value in reversed(moving_average) if value is not None), None)

    current = numeric[-1]
    previous = numeric[-2] if len(numeric) > 1 else None
    relative = current / average if average else None
    change_pct = ((current - previous) / previous * 100) if previous else None
    return VolumeStats(current, average, relative, change_pct, moving_average)
