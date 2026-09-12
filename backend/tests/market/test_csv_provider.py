"""CSV provider tests (parsing, validation, error reporting)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.market.enums import ProviderStatus, Timeframe
from app.market.exceptions import AssetNotFoundError, InvalidMarketDataError
from app.market.providers.csv import CsvMarketDataProvider

from .conftest import CSV_DIR, CSV_SINGLE_FILE, make_market_settings

WIDE_START = datetime(2025, 1, 1, tzinfo=UTC)
WIDE_END = datetime(2025, 1, 31, tzinfo=UTC)


def _provider(path, **overrides) -> CsvMarketDataProvider:  # noqa: ANN001
    return CsvMarketDataProvider(make_market_settings(CSV_MARKET_DATA_PATH=str(path), **overrides))


async def test_loads_and_sorts_candles() -> None:
    provider = _provider(CSV_DIR)
    candles = await provider.get_candles("AAPL", Timeframe.ONE_HOUR, WIDE_START, WIDE_END)
    assert len(candles) == 8
    assert candles == sorted(candles, key=lambda c: c.open_time)
    assert candles[0].open_time == datetime(2025, 1, 2, 14, tzinfo=UTC)
    assert candles[-1].close == Decimal("103.2000")


async def test_quote_derived_from_latest_candle() -> None:
    provider = _provider(CSV_DIR)
    quote = await provider.get_quote("AAPL")
    assert quote.symbol == "AAPL"
    assert quote.last == Decimal("103.2000")
    assert quote.previous_close == Decimal("102.5000")
    assert quote.bid is not None and quote.ask is not None and quote.bid < quote.ask


async def test_limit_returns_most_recent() -> None:
    provider = _provider(CSV_DIR)
    candles = await provider.get_candles(
        "AAPL", Timeframe.ONE_HOUR, WIDE_START, WIDE_END, limit=3
    )
    assert len(candles) == 3
    assert candles[-1].close == Decimal("103.2000")


async def test_missing_file_raises_not_found() -> None:
    provider = _provider(CSV_DIR)
    with pytest.raises(AssetNotFoundError):
        await provider.get_candles("NOPE", Timeframe.ONE_HOUR, WIDE_START, WIDE_END)


async def test_malformed_candle_rejected() -> None:
    provider = _provider(CSV_DIR)
    with pytest.raises(InvalidMarketDataError):
        await provider.get_candles("BAD", Timeframe.ONE_HOUR, WIDE_START, WIDE_END)


async def test_duplicate_timestamps_rejected() -> None:
    provider = _provider(CSV_DIR)
    with pytest.raises(InvalidMarketDataError):
        await provider.get_candles("DUP", Timeframe.ONE_HOUR, WIDE_START, WIDE_END)


async def test_missing_required_columns_rejected() -> None:
    provider = _provider(CSV_DIR)
    with pytest.raises(InvalidMarketDataError):
        await provider.get_candles("MISSING", Timeframe.ONE_HOUR, WIDE_START, WIDE_END)


async def test_naive_timestamp_treated_as_utc() -> None:
    provider = _provider(CSV_DIR)
    candles = await provider.get_candles("NAIVE", Timeframe.ONE_HOUR, WIDE_START, WIDE_END)
    assert len(candles) == 2
    assert candles[0].open_time.tzinfo is UTC


async def test_single_file_mode_filters_by_symbol_and_timeframe() -> None:
    provider = _provider(CSV_SINGLE_FILE)
    aapl = await provider.get_candles("AAPL", Timeframe.ONE_HOUR, WIDE_START, WIDE_END)
    msft = await provider.get_candles("MSFT", Timeframe.ONE_HOUR, WIDE_START, WIDE_END)
    assert len(aapl) == 3
    assert len(msft) == 2
    assert all(c.symbol == "MSFT" for c in msft)


async def test_search_and_health() -> None:
    provider = _provider(CSV_DIR)
    symbols = {result.symbol for result in await provider.search_assets("")}
    assert {"AAPL", "DUP", "NAIVE"} <= symbols
    health = await provider.health_check()
    assert health.status is ProviderStatus.CONNECTED


async def test_unconfigured_path_is_unhealthy() -> None:
    provider = _provider("")
    health = await provider.health_check()
    assert health.status is ProviderStatus.DISCONNECTED
