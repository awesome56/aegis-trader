"""Paper broker advanced orders, cancellation and partial fills."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.brokers.exceptions import (
    OrderNotCancellableError,
    OrderNotFoundError,
    UnsupportedOrderTypeError,
)
from app.brokers.types import BrokerOrderRequest
from app.models.enums import OrderStatus, OrderType, TradeSide


async def _cash(env) -> Decimal:  # noqa: ANN001
    return (await env.broker.get_account()).cash


async def test_limit_buy_immediate_fill(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    ask = (await env.market.get_quote("AAPL")).ask
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("5"),
            limit_price=ask + Decimal("10"),
            idempotency_key="lim-1",
        )
    )
    assert result.status is OrderStatus.FILLED
    assert result.average_fill_price == ask


async def test_limit_buy_remains_open_when_below_market(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    ask = (await env.market.get_quote("AAPL")).ask
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("5"),
            limit_price=ask - Decimal("10"),
            idempotency_key="lim-2",
        )
    )
    assert result.status is OrderStatus.SUBMITTED
    assert result.filled_quantity == Decimal("0")
    # Never eligible -> processing leaves it open and does not spend cash.
    fills = await env.broker.process_open_orders()
    assert fills == []
    assert (await env.broker.get_order(result.order_id)).status is OrderStatus.SUBMITTED


async def test_limit_sell_immediate_fill(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="b"
        )
    )
    bid = (await env.market.get_quote("AAPL")).bid
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("5"),
            limit_price=bid - Decimal("10"),
            idempotency_key="ls-1",
        )
    )
    assert result.status is OrderStatus.FILLED
    assert result.average_fill_price == bid


async def test_limit_sell_remains_open_above_market(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="b"
        )
    )
    bid = (await env.market.get_quote("AAPL")).bid
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("5"),
            limit_price=bid + Decimal("10"),
            idempotency_key="ls-2",
        )
    )
    assert result.status is OrderStatus.SUBMITTED


async def test_buy_stop_triggers_and_fills(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    last = (await env.market.get_quote("AAPL")).last
    ask = (await env.market.get_quote("AAPL")).ask
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.BUY,
            order_type=OrderType.STOP,
            quantity=Decimal("5"),
            stop_price=last - Decimal("1"),
            idempotency_key="stop-1",
        )
    )
    assert result.status is OrderStatus.FILLED
    assert result.average_fill_price == ask


async def test_buy_stop_not_triggered_stays_open(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    last = (await env.market.get_quote("AAPL")).last
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.BUY,
            order_type=OrderType.STOP,
            quantity=Decimal("5"),
            stop_price=last + Decimal("50"),
            idempotency_key="stop-2",
        )
    )
    assert result.status is OrderStatus.SUBMITTED


async def test_sell_stop_triggers(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="b"
        )
    )
    last = (await env.market.get_quote("AAPL")).last
    bid = (await env.market.get_quote("AAPL")).bid
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.SELL,
            order_type=OrderType.STOP,
            quantity=Decimal("5"),
            stop_price=last + Decimal("1"),
            idempotency_key="sstop",
        )
    )
    assert result.status is OrderStatus.FILLED
    assert result.average_fill_price == bid


async def test_stop_limit_triggers_but_limit_not_eligible(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    last = (await env.market.get_quote("AAPL")).last
    ask = (await env.market.get_quote("AAPL")).ask
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.BUY,
            order_type=OrderType.STOP_LIMIT,
            quantity=Decimal("5"),
            stop_price=last - Decimal("1"),  # triggered
            limit_price=ask - Decimal("10"),  # but limit unreachable
            idempotency_key="sl",
        )
    )
    assert result.status is OrderStatus.SUBMITTED
    assert result.filled_quantity == Decimal("0")


async def test_partial_fill_then_completion(broker_env) -> None:  # noqa: ANN001
    env = await broker_env(BROKER_PAPER_PARTIAL_FILLS=True, BROKER_PAPER_PARTIAL_FILL_RATIO=0.5)
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="pf"
        )
    )
    assert result.status is OrderStatus.PARTIALLY_FILLED
    assert result.filled_quantity == Decimal("5")
    assert result.remaining_quantity == Decimal("5")

    fills = await env.broker.process_open_orders()
    assert len(fills) == 1
    final = await env.broker.get_order(result.order_id)
    assert final.status is OrderStatus.FILLED
    assert final.filled_quantity == Decimal("10")
    assert len(await env.broker.get_orders()) == 1


async def test_cancel_pending_order_releases_reservation(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    ask = (await env.market.get_quote("AAPL")).ask
    limit = ask - Decimal("10")
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("10"),
            limit_price=limit,
            idempotency_key="cancel-1",
        )
    )
    assert await env.broker.get_buying_power() < Decimal("100000")
    cancelled = await env.broker.cancel_order(result.order_id)
    assert cancelled.status is OrderStatus.CANCELLED
    assert await env.broker.get_buying_power() == Decimal("100000")


async def test_cannot_cancel_filled_order(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("1"), idempotency_key="f"
        )
    )
    with pytest.raises(OrderNotCancellableError):
        await env.broker.cancel_order(result.order_id)


async def test_cannot_cancel_twice(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    ask = (await env.market.get_quote("AAPL")).ask
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1"),
            limit_price=ask - Decimal("5"),
            idempotency_key="twice",
        )
    )
    await env.broker.cancel_order(result.order_id)
    with pytest.raises(OrderNotCancellableError):
        await env.broker.cancel_order(result.order_id)


async def test_unknown_order_raises(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    with pytest.raises(OrderNotFoundError):
        await env.broker.get_order("11111111-1111-4111-8111-111111111111")


async def test_order_listing_and_status_filter(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    ask = (await env.market.get_quote("AAPL")).ask
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("1"), idempotency_key="a"
        )
    )
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1"),
            limit_price=ask - Decimal("5"),
            idempotency_key="b",
        )
    )
    assert len(await env.broker.get_orders()) == 2
    filled = await env.broker.get_orders(status="FILLED")
    assert len(filled) == 1


async def test_unsupported_order_type_raises(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    # model_construct bypasses enum validation to simulate a provider/edge value.
    request = BrokerOrderRequest.model_construct(
        symbol="AAPL",
        side=TradeSide.BUY,
        order_type="TRAILING_STOP",
        quantity=Decimal("1"),
    )
    with pytest.raises(UnsupportedOrderTypeError):
        await env.broker.submit_order(request)
