"""Real provider parsing tests (offline via httpx MockTransport)."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from app.core.config import get_settings
from app.market.enums import Timeframe
from app.market.exceptions import (
    AssetNotFoundError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
)
from app.market.providers.alpaca import AlpacaMarketDataProvider
from app.market.providers.kraken import KrakenProvider
from app.market.providers.twelve_data import TwelveDataProvider
from app.market.sessions import is_market_open
from app.market.validation import detect_asset_class, external_symbol
from app.models.enums import AssetClass


def _client(handler) -> httpx.AsyncClient:  # noqa: ANN001
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _settings(**overrides):
    return get_settings().model_copy(update=overrides)


def test_symbol_and_asset_class_mapping() -> None:
    assert external_symbol("BTC/USD", "kraken") == "XBTUSD"
    assert external_symbol("EUR/USD", "twelvedata") == "EUR/USD"
    assert detect_asset_class("AAPL") is AssetClass.EQUITY
    assert detect_asset_class("SPY") is AssetClass.ETF
    assert detect_asset_class("EUR/USD") is AssetClass.FOREX
    assert detect_asset_class("BTC/USD") is AssetClass.CRYPTO


async def test_twelve_data_quote_and_candles() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("apikey") == "test-key"
        if request.url.path.endswith("/quote"):
            return httpx.Response(
                200,
                json={
                    "symbol": "AAPL",
                    "open": "188.0",
                    "high": "192.0",
                    "low": "187.0",
                    "close": "190.0",
                    "previous_close": "188.0",
                    "volume": "1000",
                    "currency": "USD",
                    "datetime": "2026-01-15 15:00:00",
                },
            )
        return httpx.Response(
            200,
            json={
                "values": [
                    {
                        "datetime": "2026-01-15 14:00:00",
                        "open": "188", "high": "189", "low": "187",
                        "close": "188.5", "volume": "900",
                    },
                    {
                        "datetime": "2026-01-15 15:00:00",
                        "open": "188.5", "high": "191", "low": "188",
                        "close": "190", "volume": "1000",
                    },
                ]
            },
        )

    provider = TwelveDataProvider(
        _settings(TWELVE_DATA_API_KEY="test-key"), client=_client(handler)
    )
    quote = await provider.get_quote("AAPL")
    assert quote.last == quote.last.quantize(quote.last)
    assert str(quote.last) == "190.0000"
    assert str(quote.previous_close) == "188.0000"

    candles = await provider.get_latest_candles("AAPL", Timeframe.ONE_HOUR, 10)
    assert len(candles) == 2
    assert candles[0].open_time < candles[1].open_time
    assert str(candles[1].close) == "190.0000"


async def test_twelve_data_missing_key_raises() -> None:
    provider = TwelveDataProvider(
        _settings(TWELVE_DATA_API_KEY=""), client=_client(lambda r: httpx.Response(200, json={}))
    )
    with pytest.raises(ProviderAuthenticationError):
        await provider.get_quote("AAPL")


async def test_twelve_data_unknown_symbol() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"status": "error", "code": 404, "message": "symbol not found"}
        )

    provider = TwelveDataProvider(_settings(TWELVE_DATA_API_KEY="k"), client=_client(handler))
    with pytest.raises(AssetNotFoundError):
        await provider.get_quote("NOPE")


async def test_kraken_quote_and_candles() -> None:
    now = int(datetime(2026, 1, 15, 15, tzinfo=UTC).timestamp())
    base = now - 3600 * 2

    def handler(request: httpx.Request) -> httpx.Response:
        if "Ticker" in request.url.path:
            assert request.url.params.get("pair") == "XBTUSD"
            return httpx.Response(
                200,
                json={
                    "error": [],
                    "result": {
                        "XXBTZUSD": {
                            "a": ["50001.0", "1", "1"],
                            "b": ["49999.0", "1", "1"],
                            "c": ["50000.0", "0.1"],
                            "v": ["10.0", "100.0"],
                            "o": "49000.0",
                            "h": ["50100.0", "50500.0"],
                            "l": ["48900.0", "48000.0"],
                        }
                    },
                },
            )
        return httpx.Response(
            200,
            json={
                "error": [],
                "result": {
                    "XXBTZUSD": [
                        [base, "49000", "49200", "48800", "49100", "49000", "5.0", 10],
                        [base + 3600, "49100", "50100", "49000", "50000", "49500", "6.0", 12],
                    ]
                },
            },
        )

    provider = KrakenProvider(_settings(), client=_client(handler))
    quote = await provider.get_quote("BTC/USD")
    assert str(quote.last) == "50000.0000"
    assert str(quote.bid) == "49999.0000"

    candles = await provider.get_latest_candles("BTC/USD", Timeframe.ONE_HOUR, 10)
    assert len(candles) == 2
    assert str(candles[-1].close) == "50000.0000"
    assert candles[0].open_time == datetime.fromtimestamp(base, tz=UTC)


async def test_kraken_unknown_pair() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": ["EQuery:Unknown asset pair"], "result": {}})

    provider = KrakenProvider(_settings(), client=_client(handler))
    with pytest.raises(AssetNotFoundError):
        await provider.get_quote("NOPE/USD")


# --- Alpaca market data (equities; same venue as execution) -----------------
_SNAPSHOT = {
    "latestQuote": {"t": "2026-01-15T15:00:00Z", "bp": "100.10", "ap": "100.30"},
    "latestTrade": {"t": "2026-01-15T15:00:00Z", "p": "100.20"},
    "dailyBar": {
        "t": "2026-01-15T14:30:00Z",
        "o": "99.00",
        "h": "101.00",
        "l": "98.50",
        "c": "100.20",
        "v": "123456",
    },
    "prevDailyBar": {"c": "98.00"},
}

_BARS = [
    {"t": "2026-01-15T14:00:00Z", "o": "1.0", "h": "2.0", "l": "0.5", "c": "1.5", "v": "10", "n": 3, "vw": "1.4"},  # noqa: E501
    {"t": "2026-01-15T15:00:00Z", "o": "1.5", "h": "3.0", "l": "1.0", "c": "2.5", "v": "20", "n": 4, "vw": "2.4"},  # noqa: E501
    {"t": "2026-01-15T16:00:00Z", "o": "2.5", "h": "4.0", "l": "2.0", "c": "3.5", "v": "30", "n": 5, "vw": "3.4"},  # noqa: E501
    {"t": "2026-01-15T17:00:00Z", "o": "3.5", "h": "5.0", "l": "3.0", "c": "4.5", "v": "40", "n": 6, "vw": "4.4"},  # noqa: E501
]


def _alpaca_settings(**overrides):  # noqa: ANN001, ANN202
    base = {"ALPACA_DATA_API_KEY": "test-key", "ALPACA_DATA_API_SECRET": "test-secret"}
    base.update(overrides)
    return _settings(**base)


async def test_alpaca_quote_maps_snapshot() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["APCA-API-KEY-ID"] == "test-key"
        assert request.url.path == "/v2/stocks/AAPL/snapshot"
        assert request.url.params.get("feed") == "iex"
        return httpx.Response(200, json=_SNAPSHOT)

    provider = AlpacaMarketDataProvider(_alpaca_settings(), client=_client(handler))
    quote = await provider.get_quote("aapl")

    assert quote.symbol == "AAPL"
    assert str(quote.bid) == "100.10"
    assert str(quote.ask) == "100.30"
    assert str(quote.last) == "100.20"
    assert str(quote.open) == "99.00"
    assert str(quote.high) == "101.00"
    assert str(quote.low) == "98.50"
    assert str(quote.previous_close) == "98.00"
    assert quote.volume == 123456
    assert quote.provider == "alpaca"
    # Freshness is anchored to the exchange timestamp, not the wall clock.
    assert quote.market_timestamp == datetime(2026, 1, 15, 15, 0, tzinfo=UTC)


async def test_alpaca_quote_without_price_is_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"latestQuote": {}, "latestTrade": {}})

    provider = AlpacaMarketDataProvider(_alpaca_settings(), client=_client(handler))
    with pytest.raises(AssetNotFoundError):
        await provider.get_quote("AAPL")


async def test_alpaca_requires_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        return httpx.Response(200, json=_SNAPSHOT)

    provider = AlpacaMarketDataProvider(
        _settings(ALPACA_DATA_API_KEY="", ALPACA_DATA_API_SECRET=""), client=_client(handler)
    )
    with pytest.raises(ProviderAuthenticationError):
        await provider.get_quote("AAPL")


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, ProviderAuthenticationError),
        (403, ProviderAuthenticationError),
        (429, ProviderRateLimitError),
    ],
)
async def test_alpaca_http_errors_are_normalised(status: int, expected: type[Exception]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"message": "nope"})

    provider = AlpacaMarketDataProvider(_alpaca_settings(), client=_client(handler))
    with pytest.raises(expected):
        await provider.get_quote("AAPL")


async def test_alpaca_bars_map_and_sort_ascending() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/stocks/AAPL/bars"
        assert request.url.params.get("timeframe") == "1Hour"
        return httpx.Response(200, json={"bars": list(reversed(_BARS))})

    provider = AlpacaMarketDataProvider(_alpaca_settings(), client=_client(handler))
    candles = await provider.get_latest_candles("AAPL", Timeframe.ONE_HOUR, 10)

    assert [str(c.open) for c in candles] == ["1.0", "1.5", "2.5", "3.5"]
    assert candles[0].volume == 10
    assert candles[-1].trade_count == 6
    assert candles[-1].open_time < candles[-1].close_time if candles[-1].close_time else True


async def test_alpaca_aggregates_four_hour_candles() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("timeframe") == "1Hour"
        assert request.url.params.get("limit") == "4"
        return httpx.Response(200, json={"bars": _BARS})

    provider = AlpacaMarketDataProvider(_alpaca_settings(), client=_client(handler))
    candles = await provider.get_latest_candles("AAPL", Timeframe.FOUR_HOURS, 1)

    assert len(candles) == 1
    candle = candles[0]
    assert candle.timeframe is Timeframe.FOUR_HOURS
    assert str(candle.open) == "1.0"
    assert str(candle.close) == "4.5"
    assert str(candle.high) == "5.0"
    assert str(candle.low) == "0.5"
    assert candle.volume == 100


async def test_alpaca_market_status_matches_equity_sessions() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        return httpx.Response(200, json=_SNAPSHOT)

    provider = AlpacaMarketDataProvider(_alpaca_settings(), client=_client(handler))
    status = await provider.get_market_status()
    assert status.provider == "alpaca"
    assert status.is_open is is_market_open(AssetClass.EQUITY)
