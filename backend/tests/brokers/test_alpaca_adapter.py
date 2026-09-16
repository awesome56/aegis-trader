"""Alpaca adapter tests.

Pure mapping is exercised directly; transport is exercised with
``httpx.MockTransport`` so no test ever touches the network.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from app.brokers.alpaca import mapping
from app.brokers.alpaca.adapter import AlpacaBrokerAdapter
from app.brokers.alpaca.client import ALPACA_TRADING_BASE_URLS, AlpacaClient
from app.brokers.bootstrap import ensure_account_portfolio
from app.brokers.exceptions import (
    BrokerAuthenticationError,
    BrokerConfigurationError,
    BrokerRejectedOrderError,
    BrokerUnavailableError,
    InsufficientFundsError,
)
from app.models.broker import BrokerAccount
from app.models.enums import (
    BrokerEnvironment,
    OrderStatus,
    OrderType,
    PositionSide,
    TimeInForce,
    TradeSide,
)
from app.repositories.position import PositionRepository

from tests.brokers.conftest import broker_settings

ACCOUNT_PAYLOAD: dict[str, Any] = {
    "id": "acc-1",
    "account_number": "PA3TEST",
    "currency": "USD",
    "cash": "25000.55",
    "buying_power": "100000.00",
    "portfolio_value": "51234.10",
    "equity": "51234.10",
    "long_market_value": "26233.55",
    "short_market_value": "0",
}

POSITION_PAYLOAD: dict[str, Any] = {
    "symbol": "AAPL",
    "qty": "10",
    "avg_entry_price": "150.25",
    "current_price": "155.00",
    "market_value": "1550.00",
    "cost_basis": "1502.50",
    "unrealized_pl": "47.50",
    "unrealized_plpc": "0.0316",
}

ORDER_PAYLOAD: dict[str, Any] = {
    "id": "ord-abc",
    "client_order_id": "idem-1",
    "symbol": "AAPL",
    "side": "buy",
    "type": "limit",
    "time_in_force": "day",
    "qty": "5",
    "filled_qty": "5",
    "limit_price": "150.00",
    "stop_price": None,
    "filled_avg_price": "150.10",
    "status": "filled",
    "created_at": "2026-01-15T15:00:00Z",
    "updated_at": "2026-01-15T15:00:05Z",
    "submitted_at": "2026-01-15T15:00:01Z",
    "filled_at": "2026-01-15T15:00:05Z",
    "canceled_at": None,
}


def _client(
    handler: Any, *, environment: BrokerEnvironment = BrokerEnvironment.DEMO
) -> AlpacaClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    return AlpacaClient(
        api_key="key-1234", api_secret="secret", environment=environment, client=http
    )


def _account(environment: BrokerEnvironment = BrokerEnvironment.DEMO) -> BrokerAccount:
    now = datetime.now(UTC)
    return BrokerAccount(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        broker="alpaca",
        account_name="Alpaca Test",
        environment=environment,
        cash_balance=Decimal("0"),
        buying_power=Decimal("0"),
        currency="USD",
        created_at=now,
        updated_at=now,
    )


# --- mapping ----------------------------------------------------------------
def test_map_account_uses_decimal_and_derives_market_value() -> None:
    state = mapping.map_account(
        ACCOUNT_PAYLOAD,
        broker_account_id=uuid.uuid4(),
        environment=BrokerEnvironment.DEMO,
    )
    assert state.cash == Decimal("25000.55")
    assert state.buying_power == Decimal("100000.00")
    assert state.equity == Decimal("51234.10")
    assert state.market_value == Decimal("26233.55")
    assert state.external_account_id == "PA3TEST"
    assert state.currency == "USD"


def test_map_position_handles_shorts_and_percent() -> None:
    long_pos = mapping.map_position(POSITION_PAYLOAD)
    assert long_pos.side is PositionSide.LONG
    assert long_pos.quantity == Decimal("10")
    assert long_pos.unrealized_pnl_percent == Decimal("3.1600")

    short_pos = mapping.map_position({**POSITION_PAYLOAD, "qty": "-4"})
    assert short_pos.side is PositionSide.SHORT
    assert short_pos.quantity == Decimal("4")


def test_map_order_status_type_and_fill() -> None:
    result = mapping.map_order(ORDER_PAYLOAD, order_id=uuid.uuid4())
    assert result.status is OrderStatus.FILLED
    assert result.order_type is OrderType.LIMIT
    assert result.time_in_force is TimeInForce.DAY
    assert result.side is TradeSide.BUY
    assert result.broker_order_id == "ord-abc"
    assert result.client_order_id == "idem-1"
    assert result.average_fill_price == Decimal("150.10")
    assert result.filled_quantity == Decimal("5")
    assert result.remaining_quantity == Decimal("0")
    assert result.cancelled_at is None


def test_unknown_status_fails_safe_to_submitted() -> None:
    assert mapping.map_status("something_new") is OrderStatus.SUBMITTED


def test_to_alpaca_order_payload_carries_idempotency_key() -> None:
    payload = mapping.to_alpaca_order_payload(
        symbol="aapl",
        side=TradeSide.BUY,
        order_type=OrderType.STOP_LIMIT,
        quantity=Decimal("2.5"),
        time_in_force=TimeInForce.GTC,
        limit_price=Decimal("150"),
        stop_price=Decimal("149"),
        client_order_id="idem-9",
    )
    assert payload["symbol"] == "AAPL"
    assert payload["side"] == "buy"
    assert payload["type"] == "stop_limit"
    assert payload["time_in_force"] == "gtc"
    assert payload["qty"] == "2.5"
    assert payload["limit_price"] == "150"
    assert payload["stop_price"] == "149"
    assert payload["client_order_id"] == "idem-9"


def test_map_quote_is_stale_from_exchange_timestamp() -> None:
    now = datetime(2026, 1, 15, 15, 0, 0, tzinfo=UTC)
    fresh = mapping.map_quote(
        {
            "latestTrade": {"t": now.isoformat(), "p": "100.50"},
            "latestQuote": {"t": now.isoformat(), "bp": "100.40", "ap": "100.60"},
        },
        symbol="AAPL",
        received_at=now,
        stale_after_seconds=60,
    )
    assert fresh.bid == Decimal("100.40")
    assert fresh.ask == Decimal("100.60")
    assert fresh.last == Decimal("100.50")
    assert fresh.mid == Decimal("100.50")
    assert fresh.is_stale is False

    old = mapping.map_quote(
        {"latestTrade": {"t": (now - timedelta(minutes=5)).isoformat(), "p": "100.50"}},
        symbol="AAPL",
        received_at=now,
        stale_after_seconds=60,
    )
    assert old.is_stale is True


def test_map_clock_reports_session() -> None:
    clock = mapping.map_clock(
        {
            "is_open": True,
            "timestamp": "2026-01-15T15:00:00Z",
            "next_open": "2026-01-16T14:30:00Z",
            "next_close": "2026-01-15T21:00:00Z",
        }
    )
    assert clock.is_open is True
    assert clock.session == "regular"
    assert clock.provider == "alpaca"


# --- client -----------------------------------------------------------------
def test_client_requires_credentials() -> None:
    with pytest.raises(BrokerConfigurationError):
        AlpacaClient(api_key=None, api_secret="x", environment=BrokerEnvironment.DEMO)


def test_client_selects_environment_base_url() -> None:
    assert (
        AlpacaClient(
            api_key="k", api_secret="s", environment=BrokerEnvironment.DEMO
        ).trading_base_url
        == ALPACA_TRADING_BASE_URLS[BrokerEnvironment.DEMO]
    )
    assert (
        AlpacaClient(
            api_key="k", api_secret="s", environment=BrokerEnvironment.LIVE
        ).trading_base_url
        == ALPACA_TRADING_BASE_URLS[BrokerEnvironment.LIVE]
    )


async def test_client_sends_auth_headers() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.headers))
        return httpx.Response(200, json=ACCOUNT_PAYLOAD)

    client = _client(handler)
    try:
        await client.get_account()
    finally:
        await client.aclose()
    assert seen["apca-api-key-id"] == "key-1234"
    assert seen["apca-api-secret-key"] == "secret"


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (401, {"message": "unauthorized"}, BrokerAuthenticationError),
        (403, {"message": "forbidden"}, BrokerAuthenticationError),
        (422, {"message": "insufficient buying power"}, InsufficientFundsError),
        (422, {"message": "not enough qty"}, BrokerRejectedOrderError),
        (500, {"message": "boom"}, BrokerUnavailableError),
    ],
)
async def test_client_normalises_provider_errors(
    status: int, body: dict[str, Any], expected: type[Exception]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    client = _client(handler)
    try:
        with pytest.raises(expected):
            await client.get_account()
    finally:
        await client.aclose()


async def test_client_transport_error_is_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    client = _client(handler)
    try:
        with pytest.raises(BrokerUnavailableError):
            await client.get_account()
    finally:
        await client.aclose()


async def test_client_returns_none_for_missing_position() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "position does not exist"})

    client = _client(handler)
    try:
        assert await client.get_position("AAPL") is None
    finally:
        await client.aclose()


# --- adapter ----------------------------------------------------------------
async def _bound_adapter(db_session, handler, *, environment=BrokerEnvironment.DEMO):
    """Persist an account + its portfolio and bind an adapter to a mock transport."""
    account = _account(environment)
    db_session.add(account)
    await db_session.flush()
    portfolio = await ensure_account_portfolio(db_session, account)
    adapter = AlpacaBrokerAdapter(
        db_session, account, portfolio, _client(handler, environment=environment),
        settings=broker_settings(),
    )
    return adapter, account, portfolio


async def test_adapter_reads_account_positions_quote_and_clock(db_session) -> None:
    now = datetime.now(UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v2/account":
            return httpx.Response(200, json=ACCOUNT_PAYLOAD)
        if path == "/v2/positions":
            return httpx.Response(200, json=[POSITION_PAYLOAD])
        if path == "/v2/positions/AAPL":
            return httpx.Response(200, json=POSITION_PAYLOAD)
        if path == "/v2/clock":
            return httpx.Response(200, json={"is_open": False, "timestamp": now.isoformat()})
        if path == "/v2/stocks/AAPL/snapshot":
            return httpx.Response(
                200,
                json={
                    "latestQuote": {"t": now.isoformat(), "bp": "100.0", "ap": "100.2"},
                    "latestTrade": {"t": now.isoformat(), "p": "100.1"},
                },
            )
        return httpx.Response(404, json={"message": "unknown path"})

    adapter, _, portfolio = await _bound_adapter(db_session, handler)
    try:
        state = await adapter.get_account()
        assert state.cash == Decimal("25000.55")
        assert await adapter.get_balance() == Decimal("25000.55")
        assert await adapter.get_buying_power() == Decimal("100000.00")

        positions = await adapter.get_positions()
        assert [p.symbol for p in positions] == ["AAPL"]
        assert (await adapter.get_position("aapl")).symbol == "AAPL"  # type: ignore[union-attr]

        quote = await adapter.get_quote("aapl")
        assert quote.last == Decimal("100.1")
        assert quote.provider == "alpaca"

        clock = await adapter.get_market_clock()
        assert clock.is_open is False

        # Remote positions are mirrored into the account's own portfolio.
        mirrored = await PositionRepository(db_session).list_open(portfolio.id)
        assert [(p.symbol, p.quantity) for p in mirrored] == [("AAPL", Decimal("10"))]
    finally:
        await adapter.aclose()


async def test_adapter_does_not_mirror_positions_into_the_default_portfolio(
    db_session,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/positions":
            return httpx.Response(200, json=[POSITION_PAYLOAD])
        return httpx.Response(404, json={"message": "unknown path"})

    adapter, _, portfolio = await _bound_adapter(db_session, handler)
    try:
        await adapter.get_positions()
    finally:
        await adapter.aclose()
    assert portfolio.is_default is False
    assert portfolio.broker_account_id is not None


async def test_adapter_blocks_live_while_interlock_locked(db_session) -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        return httpx.Response(200, json=ACCOUNT_PAYLOAD)

    account = _account(BrokerEnvironment.LIVE)
    db_session.add(account)
    await db_session.flush()
    portfolio = await ensure_account_portfolio(db_session, account)
    with pytest.raises(BrokerConfigurationError):
        AlpacaBrokerAdapter(
            db_session,
            account,
            portfolio,
            _client(handler, environment=BrokerEnvironment.LIVE),
            settings=broker_settings(),
        )


def test_adapter_live_serialisation_is_json_safe() -> None:
    # Guard against accidentally persisting Decimal/bytes into raw payloads.
    payload = mapping.to_alpaca_order_payload(
        symbol="AAPL",
        side=TradeSide.SELL,
        order_type=OrderType.MARKET,
        quantity=Decimal("1"),
        time_in_force=TimeInForce.DAY,
        limit_price=None,
        stop_price=None,
        client_order_id="k",
    )
    json.dumps(payload)
