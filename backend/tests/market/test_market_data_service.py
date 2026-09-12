"""MarketDataService orchestration tests (cache, persistence, safety)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from app.market.domain.models import ProviderHealth
from app.market.enums import Timeframe
from app.market.exceptions import (
    AssetNotFoundError,
    InvalidMarketDataError,
    ProviderUnavailableError,
    StaleMarketDataError,
    UnsupportedTimeframeError,
)
from app.market.providers.mock import MockMarketDataProvider
from app.market.services.market_data import MarketDataService
from app.models.asset import Asset
from app.models.market import MarketCandle
from app.models.market import MarketQuote as MarketQuoteModel
from app.repositories.asset import AssetRepository
from sqlalchemy import func, select

from .conftest import FIXED_NOW

START = FIXED_NOW - timedelta(hours=10)


class CountingProvider(MockMarketDataProvider):
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        self.quote_calls = 0
        self.candle_calls = 0
        self.latest_calls = 0

    async def get_quote(self, symbol: str):  # noqa: ANN201
        self.quote_calls += 1
        return await super().get_quote(symbol)

    async def get_candles(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        self.candle_calls += 1
        return await super().get_candles(*args, **kwargs)

    async def get_latest_candles(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        self.latest_calls += 1
        return await super().get_latest_candles(*args, **kwargs)


class StaleQuoteProvider(MockMarketDataProvider):
    async def get_quote(self, symbol: str):  # noqa: ANN201
        quote = await super().get_quote(symbol)
        old = quote.market_timestamp - timedelta(days=1)
        return quote.model_copy(update={"market_timestamp": old, "received_at": old})


class FailingLatestProvider(CountingProvider):
    async def get_latest_candles(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        raise ProviderUnavailableError("provider down")


def _service(db_session, provider, cache, freshness, settings) -> MarketDataService:  # noqa: ANN001
    return MarketDataService(
        db_session, provider=provider, cache=cache, freshness=freshness, settings=settings
    )


async def test_quote_persists_and_is_cached(
    db_session, memory_cache, freshness, market_settings  # noqa: ANN001
) -> None:
    provider = CountingProvider(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, provider, memory_cache, freshness, market_settings)

    first = await service.get_quote("AAPL")
    assert provider.quote_calls == 1
    assert first.symbol == "AAPL"

    second = await service.get_quote("AAPL")
    assert provider.quote_calls == 1  # served from cache
    assert second.last == first.last

    count = await db_session.scalar(
        select(func.count())
        .select_from(MarketQuoteModel)
        .where(MarketQuoteModel.symbol == "AAPL")
    )
    assert count == 1


async def test_quote_creates_normalised_asset(
    db_session, memory_cache, freshness, market_settings  # noqa: ANN001
) -> None:
    provider = CountingProvider(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, provider, memory_cache, freshness, market_settings)

    await service.get_quote("aapl")

    assert await AssetRepository(db_session).get_by_symbol("AAPL") is not None
    asset_count = await db_session.scalar(
        select(func.count()).select_from(Asset).where(Asset.symbol == "AAPL")
    )
    assert asset_count == 1

    await service.get_quote("AAPL")
    assert await db_session.scalar(select(func.count()).select_from(Asset)) == 1


async def test_latest_price(
    db_session, memory_cache, freshness, market_settings  # noqa: ANN001
) -> None:
    provider = CountingProvider(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, provider, memory_cache, freshness, market_settings)
    assert await service.get_latest_price("MSFT") > 0


async def test_candles_provider_then_database_and_dedupe(
    db_session, memory_cache, freshness, market_settings  # noqa: ANN001
) -> None:
    provider = CountingProvider(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, provider, memory_cache, freshness, market_settings)

    first = await service.get_candles("AAPL", "1h", START, FIXED_NOW)
    assert len(first) == 11
    assert provider.candle_calls == 1

    second = await service.get_candles("AAPL", "1h", START, FIXED_NOW)
    assert len(second) == 11
    assert provider.candle_calls == 1  # served from database

    rows = await db_session.scalar(
        select(func.count())
        .select_from(MarketCandle)
        .where(MarketCandle.symbol == "AAPL", MarketCandle.timeframe == "1h")
    )
    assert rows == 11  # no duplicates


async def test_latest_candles_are_provider_first_and_cached(
    db_session, memory_cache, freshness, market_settings  # noqa: ANN001
) -> None:
    provider = CountingProvider(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, provider, memory_cache, freshness, market_settings)

    candles = await service.get_latest_candles("MSFT", "1h", 5)
    assert len(candles) == 5
    assert provider.latest_calls == 1

    cached = await memory_cache.get_candles("MSFT", Timeframe.ONE_HOUR)
    assert cached is not None and len(cached) == 5


async def test_latest_candles_fallback_to_database(
    db_session, memory_cache, freshness, market_settings  # noqa: ANN001
) -> None:
    seed_provider = MockMarketDataProvider(market_settings, clock=lambda: FIXED_NOW)
    await _service(db_session, seed_provider, memory_cache, freshness, market_settings).get_candles(
        "AAPL", "1h", START, FIXED_NOW
    )

    failing = FailingLatestProvider(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, failing, memory_cache, freshness, market_settings)
    candles = await service.get_latest_candles("AAPL", "1h", 5)
    assert len(candles) == 5


async def test_fresh_quote_succeeds_when_recent(
    db_session, memory_cache, freshness, market_settings  # noqa: ANN001
) -> None:
    provider = CountingProvider(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, provider, memory_cache, freshness, market_settings)
    quote = await service.get_fresh_quote("AAPL")
    assert quote.symbol == "AAPL"


async def test_stale_quote_is_rejected(
    db_session, memory_cache, freshness, market_settings  # noqa: ANN001
) -> None:
    provider = StaleQuoteProvider(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, provider, memory_cache, freshness, market_settings)
    with pytest.raises(StaleMarketDataError):
        await service.get_fresh_quote("AAPL")


async def test_stale_candles_are_rejected(
    db_session, memory_cache, market_settings  # noqa: ANN001
) -> None:
    from app.market.services.freshness import MarketDataFreshnessService

    old_clock = lambda: FIXED_NOW - timedelta(days=10)  # noqa: E731
    provider = MockMarketDataProvider(market_settings, clock=old_clock)
    freshness = MarketDataFreshnessService(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, provider, memory_cache, freshness, market_settings)
    with pytest.raises(StaleMarketDataError):
        await service.get_fresh_candles("AAPL", "1h", 5)


async def test_unknown_symbol_raises(
    db_session, memory_cache, freshness, market_settings  # noqa: ANN001
) -> None:
    provider = CountingProvider(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, provider, memory_cache, freshness, market_settings)
    with pytest.raises(AssetNotFoundError):
        await service.get_quote("ZZZZ")


async def test_invalid_timeframe_and_limits(
    db_session, memory_cache, freshness, market_settings  # noqa: ANN001
) -> None:
    provider = CountingProvider(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, provider, memory_cache, freshness, market_settings)

    with pytest.raises(UnsupportedTimeframeError):
        await service.get_candles("AAPL", "3h")
    with pytest.raises(InvalidMarketDataError):
        await service.get_candles("AAPL", "1h", limit=0)
    with pytest.raises(InvalidMarketDataError):
        await service.get_candles("AAPL", "1h", limit=100_000)


async def test_status_search_and_health(
    db_session, memory_cache, freshness, market_settings  # noqa: ANN001
) -> None:
    provider = CountingProvider(market_settings, clock=lambda: FIXED_NOW)
    service = _service(db_session, provider, memory_cache, freshness, market_settings)

    status = await service.get_market_status()
    assert status.is_open is True

    search = await service.search_assets("msft")
    assert [result.symbol for result in search] == ["MSFT"]

    health = await service.health()
    assert isinstance(health, ProviderHealth)
