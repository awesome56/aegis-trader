"""Freshness / staleness tests. Age is measured from the market timestamp."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from app.market.domain.models import Candle, MarketQuote
from app.market.enums import Timeframe
from app.market.exceptions import StaleMarketDataError
from app.market.services.freshness import MarketDataFreshnessService

from .conftest import FIXED_NOW


def _service(**overrides: object) -> MarketDataFreshnessService:
    from .conftest import make_market_settings

    return MarketDataFreshnessService(make_market_settings(**overrides), clock=lambda: FIXED_NOW)


def _quote(market_timestamp, received_at=FIXED_NOW) -> MarketQuote:  # noqa: ANN001
    return MarketQuote(
        symbol="AAPL",
        last=Decimal("100"),
        bid=Decimal("99.99"),
        ask=Decimal("100.01"),
        provider="test",
        market_timestamp=market_timestamp,
        received_at=received_at,
    )


def _candle(timeframe: Timeframe, close_time) -> Candle:  # noqa: ANN001
    return Candle(
        symbol="AAPL",
        timeframe=timeframe,
        open_time=close_time - timeframe.duration,
        close_time=close_time,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        provider="test",
    )


def test_fresh_quote() -> None:
    service = _service(MAX_QUOTE_AGE_SECONDS=900)
    quote = _quote(FIXED_NOW - timedelta(seconds=10))
    assessment = service.assess_quote(quote)
    assert assessment.is_stale is False
    assert assessment.age_seconds == pytest.approx(10, abs=0.01)
    assert service.is_quote_fresh(quote) is True
    assert service.assert_quote_fresh(quote) is quote


def test_stale_quote_is_rejected() -> None:
    service = _service(MAX_QUOTE_AGE_SECONDS=15)
    quote = _quote(FIXED_NOW - timedelta(minutes=5))
    assert service.is_quote_fresh(quote) is False
    with pytest.raises(StaleMarketDataError) as excinfo:
        service.assert_quote_fresh(quote)
    assert excinfo.value.details["symbol"] == "AAPL"


def test_age_uses_market_timestamp_not_received_at() -> None:
    service = _service(MAX_QUOTE_AGE_SECONDS=15)
    # Received just now, but the exchange timestamp is old -> must be stale.
    quote = _quote(FIXED_NOW - timedelta(hours=1), received_at=FIXED_NOW)
    assert service.is_quote_fresh(quote) is False


def test_intraday_candle_freshness() -> None:
    service = _service(MAX_INTRADAY_CANDLE_AGE_SECONDS=300)
    fresh = _candle(Timeframe.ONE_HOUR, FIXED_NOW - timedelta(seconds=60))
    stale = _candle(Timeframe.ONE_HOUR, FIXED_NOW - timedelta(seconds=600))
    assert service.is_candle_fresh(fresh) is True
    assert service.is_candle_fresh(stale) is False
    with pytest.raises(StaleMarketDataError):
        service.assert_candle_fresh(stale)


def test_daily_candle_uses_daily_threshold() -> None:
    service = _service(MAX_INTRADAY_CANDLE_AGE_SECONDS=300, MAX_DAILY_CANDLE_AGE_SECONDS=86400)
    # One hour old: stale for intraday, fresh for daily.
    candle = _candle(Timeframe.ONE_DAY, FIXED_NOW - timedelta(hours=1))
    assert service.is_candle_fresh(candle) is True


def test_forex_weekend_is_market_closed_not_provider_failure() -> None:
    from datetime import UTC, datetime

    import pytest as _pytest

    from .conftest import make_market_settings

    saturday = datetime(2026, 1, 17, 12, 0, tzinfo=UTC)
    service = MarketDataFreshnessService(
        make_market_settings(MAX_QUOTE_AGE_SECONDS=15), clock=lambda: saturday
    )
    quote = _quote(saturday - timedelta(hours=6))
    assessment = service.assess_quote(quote)
    assert assessment.market_closed is True
    assert assessment.is_stale is False
    assert assessment.session == "CLOSED"
    # Execution still fails closed on a closed market.
    with _pytest.raises(StaleMarketDataError):
        service.assert_quote_fresh(_quote(saturday - timedelta(hours=6)))


def test_crypto_old_quote_is_stale_any_day() -> None:
    from datetime import UTC, datetime

    from app.market.domain.models import MarketQuote

    from .conftest import make_market_settings

    saturday = datetime(2026, 1, 17, 12, 0, tzinfo=UTC)
    service = MarketDataFreshnessService(
        make_market_settings(MAX_QUOTE_AGE_SECONDS=15), clock=lambda: saturday
    )
    quote = MarketQuote(
        symbol="BTC/USD",
        last=Decimal("50000"),
        provider="test",
        market_timestamp=saturday - timedelta(minutes=5),
        received_at=saturday,
    )
    assessment = service.assess_quote(quote)
    assert assessment.is_stale is True
    assert assessment.market_closed is False
