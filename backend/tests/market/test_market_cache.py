"""Market-data cache tests using the in-memory backend (no Redis required)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.market.domain.models import Candle, MarketQuote, MarketStatus
from app.market.enums import MarketSession, Timeframe
from app.market.services.cache import InMemoryCacheBackend, MarketDataCache

from .conftest import FIXED_NOW, make_market_settings


def _quote() -> MarketQuote:
    return MarketQuote(
        symbol="AAPL",
        last=Decimal("126.85"),
        bid=Decimal("126.84"),
        ask=Decimal("126.86"),
        volume=1000,
        provider="mock",
        market_timestamp=FIXED_NOW,
        received_at=FIXED_NOW,
    )


def _candles() -> list[Candle]:
    return [
        Candle(
            symbol="AAPL",
            timeframe=Timeframe.ONE_HOUR,
            open_time=FIXED_NOW,
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal("100.5"),
            volume=1000,
            provider="mock",
        )
    ]


def _cache(**overrides: object) -> MarketDataCache:
    return MarketDataCache(
        backend=InMemoryCacheBackend(),
        settings=make_market_settings(**overrides),
    )


async def test_quote_round_trip() -> None:
    cache = _cache()
    assert await cache.get_quote("AAPL") is None
    await cache.set_quote(_quote())
    restored = await cache.get_quote("AAPL")
    assert restored is not None
    assert restored.last == Decimal("126.8500")
    assert restored.market_timestamp == FIXED_NOW


async def test_candles_round_trip() -> None:
    cache = _cache()
    await cache.set_candles("AAPL", Timeframe.ONE_HOUR, _candles())
    restored = await cache.get_candles("AAPL", Timeframe.ONE_HOUR)
    assert restored is not None
    assert len(restored) == 1
    assert restored[0].close == Decimal("100.5000")


async def test_status_round_trip() -> None:
    cache = _cache()
    status = MarketStatus(
        is_open=True, session=MarketSession.REGULAR, timestamp=FIXED_NOW, provider="mock"
    )
    await cache.set_status(status)
    restored = await cache.get_status()
    assert restored is not None
    assert restored.is_open is True


async def test_ttl_expiry() -> None:
    clock = [1000.0]
    backend = InMemoryCacheBackend(clock=lambda: clock[0])
    cache = MarketDataCache(
        backend=backend, settings=make_market_settings(MARKET_QUOTE_CACHE_TTL_SECONDS=10)
    )
    await cache.set_quote(_quote())
    assert await cache.get_quote("AAPL") is not None
    clock[0] += 11
    assert await cache.get_quote("AAPL") is None


async def test_corrupt_payload_is_a_miss() -> None:
    backend = InMemoryCacheBackend()
    cache = MarketDataCache(backend=backend, settings=make_market_settings())
    await backend.set(cache.quote_key("AAPL"), "{not valid json", 60)
    assert await cache.get_quote("AAPL") is None


async def test_keys_are_namespaced() -> None:
    cache = _cache()
    assert cache.quote_key("aapl") == "market:quote:AAPL"
    assert cache.candles_key("aapl", Timeframe.ONE_HOUR) == "market:candles:AAPL:1h"
    assert cache.status_key() == "market:status"


def test_market_timestamp_is_utc() -> None:
    assert FIXED_NOW.tzinfo is UTC
    assert datetime(2026, 1, 15, 15, tzinfo=UTC) == FIXED_NOW
