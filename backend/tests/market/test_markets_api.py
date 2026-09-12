"""Market-data REST endpoint tests (authentication, payloads, validation)."""

from __future__ import annotations

from httpx import AsyncClient


async def test_endpoints_require_authentication(client: AsyncClient) -> None:
    paths = [
        "/api/v1/markets/status",
        "/api/v1/markets/search?q=A",
        "/api/v1/markets/AAPL/quote",
        "/api/v1/markets/AAPL/candles",
        "/api/v1/markets/AAPL/indicators",
    ]
    for path in paths:
        response = await client.get(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "authentication_error"


async def test_market_status(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get("/api/v1/markets/status")
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["is_open"] is True
    assert "session" in body


async def test_search_assets(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get("/api/v1/markets/search", params={"q": "AA"})
    assert response.status_code == 200
    assert any(item["symbol"] == "AAPL" for item in response.json())


async def test_quote_payload_and_freshness(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get("/api/v1/markets/AAPL/quote")
    assert response.status_code == 200
    body = response.json()
    for key in (
        "symbol",
        "last",
        "bid",
        "ask",
        "provider",
        "market_timestamp",
        "received_at",
        "age_seconds",
        "is_stale",
    ):
        assert key in body
    assert body["symbol"] == "AAPL"
    assert body["provider"] == "mock"


async def test_unknown_symbol_returns_404(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get("/api/v1/markets/ZZZZ/quote")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "asset_not_found"


async def test_candles_ascending_with_limit(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get(
        "/api/v1/markets/AAPL/candles", params={"timeframe": "1h", "limit": 10}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert body["timeframe"] == "1h"
    assert len(body["candles"]) == 10
    times = [candle["open_time"] for candle in body["candles"]]
    assert times == sorted(times)
    assert body["is_stale"] is False


async def test_unsupported_timeframe(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get(
        "/api/v1/markets/AAPL/candles", params={"timeframe": "3h"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_timeframe"


async def test_limit_validation(authenticated_client: AsyncClient) -> None:
    too_small = await authenticated_client.get("/api/v1/markets/AAPL/candles", params={"limit": 0})
    assert too_small.status_code == 422
    assert too_small.json()["error"]["code"] == "validation_error"

    too_large = await authenticated_client.get(
        "/api/v1/markets/AAPL/candles", params={"limit": 5000}
    )
    assert too_large.status_code == 422


async def test_indicators_payload(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get(
        "/api/v1/markets/AAPL/indicators", params={"timeframe": "1h", "limit": 120}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert body["price"] is not None
    assert body["sma"]["latest"] is not None
    assert body["rsi"]["latest"] is not None
    assert body["macd"]["latest_macd"] is not None
    assert body["bollinger"]["latest_upper"] is not None
    assert body["volume"]["current_volume"] is not None


async def test_system_status_includes_market_data(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get("/api/v1/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["market_data_provider"] == "mock"
    assert body["market_data_status"] in {"MOCK", "CONNECTED"}


async def test_health_includes_market_data(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    components = {c["name"]: c["status"] for c in response.json()["components"]}
    assert components["market_data"] == "healthy"
