"""Portfolio, positions and dashboard REST API tests."""

from __future__ import annotations

import uuid
from decimal import Decimal

from httpx import AsyncClient

BUY = {
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": "10",
    "idempotency_key": "api-buy-1",
}


async def test_endpoints_require_authentication(client: AsyncClient) -> None:
    for path in (
        "/api/v1/portfolio",
        "/api/v1/portfolio/history",
        "/api/v1/portfolio/allocation",
        "/api/v1/positions",
        "/api/v1/dashboard",
        "/api/v1/broker/account",
        "/api/v1/broker/orders",
        "/api/v1/broker/clock",
        "/api/v1/notifications",
    ):
        response = await client.get(path)
        assert response.status_code == 401, path


async def test_empty_portfolio(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get("/api/v1/portfolio")
    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["equity"]) == Decimal("100000")
    assert body["position_count"] == 0
    assert body["daily_pnl"] is None


async def test_broker_account_positions_and_dashboard(authenticated_client: AsyncClient) -> None:
    account = await authenticated_client.get("/api/v1/broker/account")
    assert account.status_code == 200
    assert account.json()["provider"] == "paper"

    clock = await authenticated_client.get("/api/v1/broker/clock")
    assert clock.status_code == 200
    assert "session" in clock.json()

    order = await authenticated_client.post("/api/v1/broker/orders", json=BUY)
    assert order.status_code == 201, order.text
    assert order.json()["status"] == "FILLED"

    positions = await authenticated_client.get("/api/v1/positions")
    assert positions.status_code == 200
    assert len(positions.json()) == 1
    position = positions.json()[0]
    assert position["symbol"] == "AAPL"

    detail = await authenticated_client.get(f"/api/v1/positions/{position['id']}")
    assert detail.status_code == 200
    assert detail.json()["symbol"] == "AAPL"

    missing = await authenticated_client.get(f"/api/v1/positions/{uuid.uuid4()}")
    assert missing.status_code == 404

    portfolio = await authenticated_client.get("/api/v1/portfolio")
    assert portfolio.json()["position_count"] == 1

    dashboard = await authenticated_client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["portfolio"]["position_count"] == 1
    assert body["availability"] == {
        "agent": False,
        "risk": False,
        "strategies": False,
        "backtesting": False,
    }
    assert body["broker_status"] == "PAPER"
    assert len(body["recent_orders"]) == 1


async def test_idempotent_order_submission(authenticated_client: AsyncClient) -> None:
    first = await authenticated_client.post("/api/v1/broker/orders", json=BUY)
    second = await authenticated_client.post("/api/v1/broker/orders", json=BUY)
    assert first.json()["order_id"] == second.json()["order_id"]
    orders = await authenticated_client.get("/api/v1/broker/orders")
    assert orders.json()["total"] == 1


async def test_order_listing_filter_and_cancel(authenticated_client: AsyncClient) -> None:
    quote = await authenticated_client.get("/api/v1/markets/AAPL/quote")
    last = Decimal(quote.json()["last"])
    limit = last - Decimal("20")
    placed = await authenticated_client.post(
        "/api/v1/broker/orders",
        json={
            "symbol": "AAPL",
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": "1",
            "limit_price": str(limit),
            "idempotency_key": "api-limit-1",
        },
    )
    assert placed.json()["status"] == "SUBMITTED"
    order_id = placed.json()["order_id"]

    listed = await authenticated_client.get("/api/v1/broker/orders?status=SUBMITTED")
    assert listed.json()["total"] == 1

    cancelled = await authenticated_client.delete(f"/api/v1/broker/orders/{order_id}")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


async def test_portfolio_history_and_allocation(authenticated_client: AsyncClient) -> None:
    await authenticated_client.post("/api/v1/broker/orders", json=BUY)
    history = await authenticated_client.get("/api/v1/portfolio/history?range=1M")
    assert history.status_code == 200
    assert history.json()["range"] == "1M"
    allocation = await authenticated_client.get("/api/v1/portfolio/allocation")
    assert allocation.status_code == 200
    assert allocation.json()["total_equity"]


async def test_invalid_candle_symbol_positions_do_not_leak(
    authenticated_client: AsyncClient,
) -> None:
    # A user with no positions must not see anything for another user.
    response = await authenticated_client.get("/api/v1/positions")
    assert response.json() == []
