"""Asset-class market sessions.

Different asset classes trade on different schedules; freshness and worker logic
must not treat crypto/forex as US equities. Times are UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime, time

from app.models.enums import AssetClass

_FOREX_CLOSE = time(21, 0)
_US_OPEN = time(13, 30)
_US_CLOSE = time(20, 0)


def is_market_open(asset_class: AssetClass, at: datetime | None = None) -> bool:
    moment = (at or datetime.now(UTC)).astimezone(UTC)
    weekday = moment.weekday()  # Mon=0 .. Sun=6
    current = moment.time()

    if asset_class is AssetClass.CRYPTO:
        return True  # 24/7 except provider maintenance

    if asset_class is AssetClass.FOREX:
        if weekday == 5:  # Saturday
            return False
        if weekday == 6:  # Sunday: opens 21:00 UTC
            return current >= _FOREX_CLOSE
        if weekday == 4:  # Friday: closes 21:00 UTC
            return current < _FOREX_CLOSE
        return True

    # Equities / ETFs: US regular session
    return weekday < 5 and _US_OPEN <= current < _US_CLOSE


def session_label(asset_class: AssetClass, at: datetime | None = None) -> str:
    return "OPEN" if is_market_open(asset_class, at) else "CLOSED"
