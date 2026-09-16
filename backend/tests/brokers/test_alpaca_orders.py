"""Alpaca order-routing tests.

A tiny in-memory fake venue sits behind ``httpx.MockTransport`` so the whole
submit → reconcile → cancel path (including idempotency) is exercised without
touching the network or a real account.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
import pytest
from app.brokers.alpaca.adapter import AlpacaBrokerAdapter
from app.brokers.alpaca.client import AlpacaClient
from app.brokers.bootstrap import ensure_account_portfolio
from app.brokers.exceptions import (
    InsufficientFundsError,
    OrderNotCancellableError,
    OrderNotFoundError,
)
from app.brokers.types import BrokerOrderRequest
from app.models.broker import BrokerAccount
from app.models.enums import BrokerEnvironment, OrderStatus, OrderType, TradeSide
from app.repositories.order import ExecutionRepository, OrderRepository

from tests.brokers.conftest import broker_settings


class FakeVenue:
    """Minimal stand-in for the Alpaca orders API."""

    def __init__(self, *, initial_status: str = "accepted") -> None:
        self.initial_status = initial_status
        self.orders: dict[str, dict[str, Any]] = {}
        self.by_client_id: dict[str, str] = {}
        self.submits = 0
        self.cancels = 0
        self.fail_with: tuple[int, dict[str, Any]] | None = None

    def remote(self, oid: str) -> dict[str, Any] | None:
        return self.orders.get(oid)

    def fill(self, oid: str, *, quantity: str, price: str) -> None:
        now = datetime.now(UTC).isoformat()
        order = self.orders[oid]
        order.update(
            {
                "status": "filled",
                "filled_qty": quantity,
                "filled_avg_price": price,
                "filled_at": now,
                "updated_at": now,
            }
        )

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method
        if method == "POST" and path == "/v2/orders":
            self.submits += 1
            if self.fail_with is not None:
                status, body = self.fail_with
                return httpx.Response(status, json=body)
            body = json.loads(request.content)
            client_id = body["client_order_id"]
            if client_id in self.by_client_id:
                return httpx.Response(
                    422, json={"message": "client_order_id must be unique"}
                )
            oid = f"ord-{self.submits}"
            now = datetime.now(UTC).isoformat()
            self.by_client_id[client_id] = oid
            self.orders[oid] = {
                "id": oid,
                "client_order_id": client_id,
                "symbol": body["symbol"],
                "side": body["side"],
                "type": body["type"],
                "time_in_force": body["time_in_force"],
                "qty": body["qty"],
                "filled_qty": "0",
                "filled_avg_price": None,
                "limit_price": body.get("limit_price"),
                "stop_price": body.get("stop_price"),
                "status": self.initial_status,
                "created_at": now,
                "submitted_at": now,
                "updated_at": now,
                "filled_at": None,
                "canceled_at": None,
            }
            return httpx.Response(200, json=self.orders[oid])
        if path.startswith("/v2/orders/"):
            oid = path.rsplit("/", 1)[-1]
            order = self.orders.get(oid)
            if order is None:
                return httpx.Response(404, json={"message": "order not found"})
            if method == "DELETE":
                self.cancels += 1
                order.update(
                    {"status": "canceled", "canceled_at": datetime.now(UTC).isoformat()}
                )
                return httpx.Response(204)
            return httpx.Response(200, json=order)
        return httpx.Response(404, json={"message": f"unknown path {path}"})


async def _adapter(db_session, venue: FakeVenue) -> tuple[AlpacaBrokerAdapter, Any]:
    account = BrokerAccount(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        broker="alpaca",
        account_name="Alpaca DEMO",
        environment=BrokerEnvironment.DEMO,
        cash_balance=Decimal("100000"),
        buying_power=Decimal("100000"),
        currency="USD",
    )
    db_session.add(account)
    await db_session.flush()
    portfolio = await ensure_account_portfolio(db_session, account)
    http = httpx.AsyncClient(transport=httpx.MockTransport(venue.handler))
    client = AlpacaClient(
        api_key="key", api_secret="secret", environment=BrokerEnvironment.DEMO, client=http
    )
    adapter = AlpacaBrokerAdapter(
        db_session, account, portfolio, client, settings=broker_settings()
    )
    return adapter, account


def _request(**overrides: Any) -> BrokerOrderRequest:
    payload: dict[str, Any] = {
        "symbol": "AAPL",
        "side": TradeSide.BUY,
        "order_type": OrderType.MARKET,
        "quantity": Decimal("3"),
        "idempotency_key": "idem-1",
    }
    payload.update(overrides)
    return BrokerOrderRequest(**payload)


async def test_submit_order_mirrors_local_order_and_carries_idempotency_key(
    db_session,
) -> None:
    venue = FakeVenue()
    adapter, account = await _adapter(db_session, venue)
    try:
        result = await adapter.submit_order(_request())
    finally:
        await adapter.aclose()

    assert venue.submits == 1
    assert result.status is OrderStatus.ACCEPTED
    assert result.broker_order_id == "ord-1"
    assert result.symbol == "AAPL"

    order = await OrderRepository(db_session).get(result.order_id)
    assert order is not None
    assert order.broker_account_id == account.id
    assert order.idempotency_key == "idem-1"
    assert order.client_order_id == "idem-1"
    assert order.raw_request is not None and order.raw_request["client_order_id"] == "idem-1"
    assert order.raw_response is not None and order.raw_response["id"] == "ord-1"


async def test_submit_order_is_idempotent_on_retry(db_session) -> None:
    venue = FakeVenue()
    adapter, _ = await _adapter(db_session, venue)
    try:
        first = await adapter.submit_order(_request())
        second = await adapter.submit_order(_request())
    finally:
        await adapter.aclose()

    # One order at the venue, one local row: a retry converges instead of doubling.
    assert venue.submits == 1
    assert first.order_id == second.order_id


async def test_rejected_submit_marks_local_order_rejected(db_session) -> None:
    venue = FakeVenue()
    venue.fail_with = (422, {"message": "insufficient buying power"})
    adapter, account = await _adapter(db_session, venue)
    try:
        with pytest.raises(InsufficientFundsError):
            await adapter.submit_order(_request())
    finally:
        await adapter.aclose()

    orders = await OrderRepository(db_session).list_for_account(account.id)
    assert len(orders) == 1
    assert orders[0].status is OrderStatus.REJECTED
    assert orders[0].error_message is not None
    assert "insufficient buying power" in orders[0].error_message


async def test_fill_reconciliation_creates_execution(db_session) -> None:
    venue = FakeVenue()
    adapter, _ = await _adapter(db_session, venue)
    try:
        submitted = await adapter.submit_order(_request())
        venue.fill("ord-1", quantity="3", price="150.25")
        fills = await adapter.process_open_orders()
        refreshed = await adapter.get_order(submitted.order_id)
    finally:
        await adapter.aclose()

    assert refreshed.status is OrderStatus.FILLED
    assert refreshed.filled_quantity == Decimal("3")
    assert refreshed.average_fill_price == Decimal("150.25")
    assert len(fills) == 1
    assert fills[0].quantity == Decimal("3")
    assert fills[0].price == Decimal("150.25")

    executions = await ExecutionRepository(db_session).list_for_order(submitted.order_id)
    assert len(executions) == 1
    assert executions[0].quantity == Decimal("3")

    # Reconciliation is not additive: a second pass adds no duplicate execution.
    assert await adapter.process_open_orders() == []
    assert len(await ExecutionRepository(db_session).list_for_order(submitted.order_id)) == 1


async def test_partial_then_full_fill_reconciles_incrementally(db_session) -> None:
    venue = FakeVenue()
    adapter, _ = await _adapter(db_session, venue)
    try:
        submitted = await adapter.submit_order(_request())
        venue.orders["ord-1"].update(
            {"status": "partially_filled", "filled_qty": "1", "filled_avg_price": "100.00"}
        )
        first = await adapter.process_open_orders()
        venue.fill("ord-1", quantity="3", price="120.00")
        second = await adapter.process_open_orders()
        final = await adapter.get_order(submitted.order_id)
    finally:
        await adapter.aclose()

    assert [f.quantity for f in first] == [Decimal("1")]
    assert [f.quantity for f in second] == [Decimal("2")]
    assert final.filled_quantity == Decimal("3")
    # Weighted average across the two fills: (1*100 + 2*120) / 3, stored at the
    # column's 10dp precision.
    assert final.average_fill_price is not None
    assert final.average_fill_price.quantize(Decimal("0.000001")) == Decimal("113.333333")


async def test_cancel_order_marks_cancelled(db_session) -> None:
    venue = FakeVenue()
    adapter, _ = await _adapter(db_session, venue)
    try:
        submitted = await adapter.submit_order(_request())
        cancelled = await adapter.cancel_order(submitted.order_id)
    finally:
        await adapter.aclose()

    assert venue.cancels == 1
    assert cancelled.status is OrderStatus.CANCELLED
    assert cancelled.cancelled_at is not None


async def test_cancel_terminal_order_is_refused(db_session) -> None:
    venue = FakeVenue()
    adapter, _ = await _adapter(db_session, venue)
    try:
        submitted = await adapter.submit_order(_request())
        venue.fill("ord-1", quantity="3", price="150")
        await adapter.process_open_orders()
        with pytest.raises(OrderNotCancellableError):
            await adapter.cancel_order(submitted.order_id)
    finally:
        await adapter.aclose()
    assert venue.cancels == 0


async def test_get_order_and_get_orders_are_account_scoped(db_session) -> None:
    venue = FakeVenue()
    adapter, _ = await _adapter(db_session, venue)
    try:
        submitted = await adapter.submit_order(_request())
        listed = await adapter.get_orders(limit=10)
        assert [o.order_id for o in listed] == [submitted.order_id]

        with pytest.raises(OrderNotFoundError):
            await adapter.get_order(uuid.uuid4())
    finally:
        await adapter.aclose()
    assert venue.submits == 1
