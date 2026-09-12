"""Paper broker: account, bootstrap, market orders, positions and P&L."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from app.brokers.accounting import q
from app.brokers.bootstrap import ensure_paper_account
from app.brokers.exceptions import (
    BrokerUnavailableError,
)
from app.brokers.paper import PaperBrokerAdapter
from app.brokers.types import BrokerOrderRequest
from app.market.exceptions import StaleMarketDataError
from app.models.broker import BrokerAccount
from app.models.enums import OrderStatus, OrderType, TradeSide
from sqlalchemy import func, select

from .conftest import FIXED_NOW


async def test_bootstrap_creates_account_and_portfolio(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    assert env.account.cash_balance == Decimal("100000.0000000000")
    assert env.portfolio.initial_capital == Decimal("100000.0000000000")
    account = await env.broker.get_account()
    assert account.cash == Decimal("100000.0000000000")
    assert account.buying_power == Decimal("100000.0000000000")
    assert account.equity == Decimal("100000.0000000000")


async def test_bootstrap_is_idempotent(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    first, first_portfolio = await ensure_paper_account(env.session, env.user, env.settings)
    second, second_portfolio = await ensure_paper_account(env.session, env.user, env.settings)
    assert first.id == second.id
    assert first_portfolio.id == second_portfolio.id
    count = await env.session.scalar(
        select(func.count()).select_from(BrokerAccount).where(BrokerAccount.user_id == env.user.id)
    )
    assert count == 1


async def test_bootstrap_disabled_refuses(db_session) -> None:  # noqa: ANN001
    import uuid

    from app.models.user import User

    from .conftest import broker_settings

    settings = broker_settings(BROKER_PAPER_AUTO_CREATE_ACCOUNT=False)
    user = User(
        email=f"no-account-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="x",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    with pytest.raises(BrokerUnavailableError):
        await ensure_paper_account(db_session, user, settings)


async def test_market_buy_fills_at_ask_and_updates_cash(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    ask = (await env.market.get_quote("AAPL")).ask
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="buy-1"
        )
    )
    assert result.status is OrderStatus.FILLED
    assert result.average_fill_price == ask
    account = await env.broker.get_account()
    assert account.cash == q(Decimal("100000") - ask * 10)
    positions = await env.broker.get_positions()
    assert len(positions) == 1
    assert positions[0].quantity == Decimal("10")
    assert positions[0].average_entry_price == ask


async def test_market_sell_fills_at_bid(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="b"
        )
    )
    env.clock[0] = FIXED_NOW + timedelta(minutes=10)
    bid = (await env.market.get_quote("AAPL")).bid
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.SELL, quantity=Decimal("10"), idempotency_key="s"
        )
    )
    assert result.status is OrderStatus.FILLED
    assert result.average_fill_price == bid
    positions = await env.broker.get_positions()
    assert positions == []


async def test_slippage_worsens_buy_and_sell(broker_env) -> None:  # noqa: ANN001
    env = await broker_env(BROKER_PAPER_SLIPPAGE_BPS=10.0)
    ask = (await env.market.get_quote("AAPL")).ask
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("5"), idempotency_key="slip"
        )
    )
    assert result.average_fill_price == q(ask * Decimal("1.001"))
    assert result.average_fill_price > ask


async def test_commission_affects_cash_and_cost_basis(broker_env) -> None:  # noqa: ANN001
    env = await broker_env(BROKER_PAPER_COMMISSION=5.0)
    ask = (await env.market.get_quote("AAPL")).ask
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="c"
        )
    )
    account = await env.broker.get_account()
    assert account.cash == q(Decimal("100000") - ask * 10 - 5)
    position = (await env.broker.get_positions())[0]
    assert position.cost_basis == q(ask * 10 + 5)
    assert position.average_entry_price == q((ask * 10 + 5) / 10)


async def test_weighted_average_entry_on_second_buy(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    ask1 = (await env.market.get_quote("AAPL")).ask
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="1"
        )
    )
    env.clock[0] = FIXED_NOW + timedelta(minutes=30)
    ask2 = (await env.market.get_quote("AAPL")).ask
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="2"
        )
    )
    assert ask1 != ask2
    position = (await env.broker.get_positions())[0]
    assert position.quantity == Decimal("20")
    assert position.average_entry_price == q((ask1 * 10 + ask2 * 10) / 20)


async def test_partial_sell_realized_pnl_and_remaining(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("20"), idempotency_key="b"
        )
    )
    entry = (await env.broker.get_positions())[0].average_entry_price
    env.clock[0] = FIXED_NOW + timedelta(minutes=45)
    bid = (await env.market.get_quote("AAPL")).bid
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.SELL, quantity=Decimal("5"), idempotency_key="s"
        )
    )
    position = (await env.broker.get_positions())[0]
    assert position.quantity == Decimal("15")
    assert position.average_entry_price == entry  # unchanged on reduction
    assert position.realized_pnl == q((bid - entry) * 5)
    account = await env.broker.get_account()
    assert account.realized_pnl == q((bid - entry) * 5)


async def test_unrealized_pnl_marks_at_bid(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="b"
        )
    )
    env.clock[0] = FIXED_NOW + timedelta(minutes=60)
    bid = (await env.market.get_quote("AAPL")).bid
    entry = (await env.broker.get_positions())[0].average_entry_price
    position = (await env.broker.get_positions())[0]
    assert position.unrealized_pnl == q((bid - entry) * 10)


async def test_insufficient_funds_rejects_order(broker_env) -> None:  # noqa: ANN001
    env = await broker_env(PAPER_INITIAL_BALANCE=100.0)
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("100"), idempotency_key="x"
        )
    )
    assert result.status is OrderStatus.REJECTED
    assert result.error_message == "Insufficient funds for order"
    account = await env.broker.get_account()
    assert account.cash == Decimal("100.0000000000")


async def test_insufficient_position_rejected_no_shorting(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    result = await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.SELL, quantity=Decimal("5"), idempotency_key="s"
        )
    )
    assert result.status is OrderStatus.REJECTED
    assert "Insufficient position" in (result.error_message or "")


async def test_idempotent_submission_returns_same_order(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    request = BrokerOrderRequest(
        symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="same-key"
    )
    first = await env.broker.submit_order(request)
    second = await env.broker.submit_order(request)
    assert first.order_id == second.order_id
    orders = await env.broker.get_orders()
    assert len(orders) == 1


async def test_persistence_across_new_adapter_instance(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("10"), idempotency_key="p"
        )
    )
    account, portfolio = await ensure_paper_account(env.session, env.user, env.settings)
    fresh = PaperBrokerAdapter(env.session, account, portfolio, env.market, settings=env.settings)
    positions = await fresh.get_positions()
    assert len(positions) == 1
    assert positions[0].quantity == Decimal("10")


async def test_stale_quote_fails_closed(broker_env) -> None:  # noqa: ANN001
    env = await broker_env(
        provider_now=FIXED_NOW - timedelta(days=1),
        freshness_now=FIXED_NOW,
        MAX_QUOTE_AGE_SECONDS=15,
    )
    with pytest.raises(StaleMarketDataError):
        await env.broker.submit_order(
            BrokerOrderRequest(
                symbol="AAPL", side=TradeSide.BUY, quantity=Decimal("1"), idempotency_key="stale"
            )
        )
    assert await env.broker.get_orders() == []


async def test_market_clock_and_quote(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    clock = await env.broker.get_market_clock()
    assert clock.is_open is True
    quote = await env.broker.get_quote("AAPL")
    assert quote.symbol == "AAPL"
    assert quote.is_stale is False


async def test_buying_power_reserves_open_buy_orders(broker_env) -> None:  # noqa: ANN001
    env = await broker_env()
    limit = (await env.market.get_quote("AAPL")).last * Decimal("0.5")  # far below -> stays open
    await env.broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("10"),
            limit_price=limit,
            idempotency_key="reserve",
        )
    )
    power = await env.broker.get_buying_power()
    assert power == q(Decimal("100000") - limit * 10)
