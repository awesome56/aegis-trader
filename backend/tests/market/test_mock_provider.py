"""Deterministic mock provider tests."""

from __future__ import annotations

from datetime import timedelta

import pytest
from app.market.enums import MarketSession, ProviderStatus, Timeframe
from app.market.exceptions import AssetNotFoundError
from app.market.providers.mock import MockMarketDataProvider

from .conftest import FIXED_NOW, make_market_settings


def _candle_tuples(candles) -> list[tuple]:  # noqa: ANN001
    return [
        (c.symbol, c.timeframe.value, c.open_time, c.open, c.high, c.low, c.close, c.volume)
        for c in candles
    ]


async def test_candles_are_deterministic_for_same_seed() -> None:
    settings = make_market_settings()
    clock = lambda: FIXED_NOW  # noqa: E731
    first = MockMarketDataProvider(settings, clock=clock)
    second = MockMarketDataProvider(settings, clock=clock)

    start = FIXED_NOW - timedelta(hours=10)
    candles_a = await first.get_candles("AAPL", Timeframe.ONE_HOUR, start, FIXED_NOW)
    candles_b = await second.get_candles("AAPL", Timeframe.ONE_HOUR, start, FIXED_NOW)

    assert _candle_tuples(candles_a) == _candle_tuples(candles_b)
    assert len(candles_a) == 11


async def test_different_seed_changes_data() -> None:
    clock = lambda: FIXED_NOW  # noqa: E731
    a = MockMarketDataProvider(make_market_settings(MOCK_MARKET_SEED=1), clock=clock)
    b = MockMarketDataProvider(make_market_settings(MOCK_MARKET_SEED=2), clock=clock)
    start = FIXED_NOW - timedelta(hours=5)
    assert _candle_tuples(await a.get_candles("AAPL", Timeframe.ONE_HOUR, start, FIXED_NOW)) != (
        _candle_tuples(await b.get_candles("AAPL", Timeframe.ONE_HOUR, start, FIXED_NOW))
    )


async def test_quote_invariants(mock_provider: MockMarketDataProvider) -> None:
    quote = await mock_provider.get_quote("AAPL")
    assert quote.symbol == "AAPL"
    assert quote.last > 0
    assert quote.bid is not None and quote.ask is not None
    assert quote.bid <= quote.last <= quote.ask
    assert quote.volume is not None and quote.volume >= 0
    assert quote.provider == "mock"
    assert quote.market_timestamp == FIXED_NOW
    assert quote.previous_close is not None


async def test_unknown_symbol_raises(mock_provider: MockMarketDataProvider) -> None:
    with pytest.raises(AssetNotFoundError):
        await mock_provider.get_quote("ZZZZ")


async def test_candle_ohlc_invariants_and_order(mock_provider: MockMarketDataProvider) -> None:
    start = FIXED_NOW - timedelta(hours=20)
    candles = await mock_provider.get_candles("MSFT", Timeframe.ONE_HOUR, start, FIXED_NOW)

    assert candles == sorted(candles, key=lambda c: c.open_time)
    for candle in candles:
        assert candle.high >= candle.open
        assert candle.high >= candle.close
        assert candle.high >= candle.low
        assert candle.low <= candle.open
        assert candle.low <= candle.close
        assert candle.volume is not None and candle.volume >= 0
        assert candle.close_time == candle.open_time + Timeframe.ONE_HOUR.duration


async def test_limit_returns_most_recent(mock_provider: MockMarketDataProvider) -> None:
    start = FIXED_NOW - timedelta(hours=50)
    candles = await mock_provider.get_candles("AAPL", Timeframe.ONE_HOUR, start, FIXED_NOW, limit=5)
    assert len(candles) == 5
    assert candles[-1].open_time == FIXED_NOW


async def test_latest_candles_align_to_now(mock_provider: MockMarketDataProvider) -> None:
    candles = await mock_provider.get_latest_candles("NVDA", Timeframe.ONE_HOUR, 6)
    assert len(candles) == 6
    assert candles[-1].open_time == FIXED_NOW


async def test_market_status(mock_provider: MockMarketDataProvider) -> None:
    status = await mock_provider.get_market_status()
    assert status.is_open is True
    assert status.session is MarketSession.REGULAR
    assert status.provider == "mock"
    assert status.opens_at is not None and status.closes_at is not None


async def test_search_assets(mock_provider: MockMarketDataProvider) -> None:
    assert [r.symbol for r in await mock_provider.search_assets("aa")] == ["AAPL"]
    assert len(await mock_provider.search_assets("")) == 3
    assert (await mock_provider.search_assets("Apple"))[0].symbol == "AAPL"


async def test_health_check(mock_provider: MockMarketDataProvider) -> None:
    health = await mock_provider.health_check()
    assert health.status is ProviderStatus.MOCK
    assert health.provider == "mock"
