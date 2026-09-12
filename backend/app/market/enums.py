"""Market-data enumerations: timeframes, sessions, provider health."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum


class Timeframe(StrEnum):
    """Canonical timeframes. Provider conversions live on the enum so timeframe
    strings are never scattered through the application."""

    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"

    @property
    def duration(self) -> timedelta:
        return _TIMEFRAME_DURATIONS[self]

    @property
    def seconds(self) -> int:
        return int(self.duration.total_seconds())

    @property
    def is_intraday(self) -> bool:
        return self.duration < timedelta(days=1)

    @classmethod
    def parse(cls, value: Timeframe | str) -> Timeframe:
        """Case-insensitive parse accepting aliases such as ``1H`` / ``1D``."""
        if isinstance(value, Timeframe):
            return value
        normalized = str(value).strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            supported = ", ".join(member.value for member in cls)
            raise ValueError(f"Unsupported timeframe {value!r}. Supported: {supported}") from exc


_TIMEFRAME_DURATIONS: dict[Timeframe, timedelta] = {
    Timeframe.ONE_MINUTE: timedelta(minutes=1),
    Timeframe.FIVE_MINUTES: timedelta(minutes=5),
    Timeframe.FIFTEEN_MINUTES: timedelta(minutes=15),
    Timeframe.THIRTY_MINUTES: timedelta(minutes=30),
    Timeframe.ONE_HOUR: timedelta(hours=1),
    Timeframe.FOUR_HOURS: timedelta(hours=4),
    Timeframe.ONE_DAY: timedelta(days=1),
    Timeframe.ONE_WEEK: timedelta(weeks=1),
}


class MarketSession(StrEnum):
    PRE_MARKET = "PRE_MARKET"
    REGULAR = "REGULAR"
    AFTER_HOURS = "AFTER_HOURS"
    CLOSED = "CLOSED"


class ProviderStatus(StrEnum):
    """Normalised health state for any market-data provider."""

    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"
    MOCK = "MOCK"
