"""Real provider parsing tests (offline via httpx MockTransport)."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from app.core.config import get_settings
from app.market.enums import Timeframe
from app.market.exceptions import AssetNotFoundError, ProviderAuthenticationError
from app.market.providers.kraken import KrakenProvider
from app.market.providers.twelve_data import TwelveDataProvider
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
