"""Indicator result types and shared helpers.

The numeric indicator functions are pure and dependency-free (no FastAPI,
SQLAlchemy, Redis, providers or LLMs). They return series aligned 1:1 with the
input, using ``None`` during the warm-up window so callers can never read an
under-computed value. ``Input`` must contain at least ``period`` finite values
for a value to appear.
"""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel


class IndicatorPoint(BaseModel):
    timestamp: datetime | None = None
    value: float


def last_value(values: list[float | None]) -> float | None:
    for value in reversed(values):
        if value is not None:
            return value
    return None


def points(timestamps: list[datetime | None], values: list[float | None]) -> list[IndicatorPoint]:
    return [
        IndicatorPoint(timestamp=ts, value=float(value))
        for ts, value in zip(timestamps, values, strict=True)
        if value is not None
    ]


class _SeriesResult(BaseModel):
    period: int
    values: list[IndicatorPoint]
    latest: float | None

    @property
    def has_sufficient_data(self) -> bool:
        return self.latest is not None


class SMAResult(_SeriesResult):
    pass


class EMAResult(_SeriesResult):
    pass


class RSIResult(_SeriesResult):
    pass


class ATRResult(_SeriesResult):
    pass


class MACDResult(BaseModel):
    fast_period: int
    slow_period: int
    signal_period: int
    macd: list[IndicatorPoint]
    signal: list[IndicatorPoint]
    histogram: list[IndicatorPoint]
    latest_macd: float | None
    latest_signal: float | None
    latest_histogram: float | None

    @property
    def has_sufficient_data(self) -> bool:
        return self.latest_macd is not None


class BollingerBandsResult(BaseModel):
    period: int
    std_dev: float
    middle: list[IndicatorPoint]
    upper: list[IndicatorPoint]
    lower: list[IndicatorPoint]
    bandwidth: list[IndicatorPoint]
    percent_b: list[IndicatorPoint]
    latest_middle: float | None
    latest_upper: float | None
    latest_lower: float | None
    latest_bandwidth: float | None
    latest_percent_b: float | None

    @property
    def has_sufficient_data(self) -> bool:
        return self.latest_middle is not None


class VolumeAnalysisResult(BaseModel):
    ma_period: int
    current_volume: float | None
    average_volume: float | None
    relative_volume: float | None
    volume_change_pct: float | None
    series: list[IndicatorPoint]


def population_std(values: list[float], mean: float) -> float:
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
