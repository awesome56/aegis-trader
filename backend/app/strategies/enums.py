"""Strategy-layer enumerations.

``SignalDirection`` and ``MarketRegime`` are reused from the domain models. The
regime is split into a **trend** axis and a **volatility** axis so strategy
gating is unambiguous, with a single ``primary`` ``MarketRegime`` retained for
persistence/API compatibility.
"""

from __future__ import annotations

from enum import StrEnum


class StrategyKey(StrEnum):
    TREND_FOLLOWING = "trend_following"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"


class EvaluationStatus(StrEnum):
    SIGNAL = "SIGNAL"
    NO_SIGNAL = "NO_SIGNAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    STALE_DATA = "STALE_DATA"


class TrendRegime(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"


class VolatilityRegime(StrEnum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
