"""Asset-class market-session tests (UTC)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.market.sessions import is_market_open, session_label
from app.models.enums import AssetClass

# 2026-01-15 is a Thursday.
THURSDAY_1500 = datetime(2026, 1, 15, 15, 0, tzinfo=UTC)  # US session open
THURSDAY_0300 = datetime(2026, 1, 15, 3, 0, tzinfo=UTC)  # US session closed
SATURDAY_1200 = datetime(2026, 1, 17, 12, 0, tzinfo=UTC)
SUNDAY_1200 = datetime(2026, 1, 18, 12, 0, tzinfo=UTC)
SUNDAY_2200 = datetime(2026, 1, 18, 22, 0, tzinfo=UTC)
FRIDAY_2200 = datetime(2026, 1, 16, 22, 0, tzinfo=UTC)


def test_crypto_is_always_open() -> None:
    for moment in (THURSDAY_0300, SATURDAY_1200, SUNDAY_1200):
        assert is_market_open(AssetClass.CRYPTO, moment) is True


def test_equities_follow_us_session() -> None:
    assert is_market_open(AssetClass.EQUITY, THURSDAY_1500) is True
    assert is_market_open(AssetClass.EQUITY, THURSDAY_0300) is False
    assert is_market_open(AssetClass.EQUITY, SATURDAY_1200) is False


def test_forex_weekend_behaviour() -> None:
    assert is_market_open(AssetClass.FOREX, THURSDAY_1500) is True
    assert is_market_open(AssetClass.FOREX, SATURDAY_1200) is False
    assert is_market_open(AssetClass.FOREX, SUNDAY_1200) is False
    assert is_market_open(AssetClass.FOREX, SUNDAY_2200) is True
    assert is_market_open(AssetClass.FOREX, FRIDAY_2200) is False


def test_session_label() -> None:
    assert session_label(AssetClass.CRYPTO, SATURDAY_1200) == "OPEN"
    assert session_label(AssetClass.FOREX, SATURDAY_1200) == "CLOSED"
