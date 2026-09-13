"""BrokerSafetyGateway tests: DEMO paper execution, permissions, risk, reduce/close."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.auto_trading.gateway import BrokerSafetyGateway
from app.auto_trading.service import AutoTradingPolicyService
from app.brokers.bootstrap import ensure_paper_account
from app.core.config import get_settings
from app.models.enums import AutoTradeAction, TradeSide, TradingState
from app.models.user import User
from app.repositories.order import OrderRepository
from app.risk.trading_state import TradingStateService


async def _user(session, email: str = "gw@example.com") -> User:
    user = User(email=email, hashed_password="x", is_active=True)
    session.add(user)
    await session.flush()
    return user


async def _setup(session, email: str, *, enable: bool = True):
    user = await _user(session, email)
    account, portfolio = await ensure_paper_account(session, user)
    policy_service = AutoTradingPolicyService(session, get_settings())
    policy = await policy_service.get_or_create(user.id, account)
    policy = await policy_service.update(
        policy, allow_open=True, allow_close=True, allow_reduce=True
    )
    if enable:
        policy = await policy_service.enable(user.id, policy, confirm=True)
    return user, account, policy


async def test_auto_off_rejects_without_order(db_session) -> None:
    user, account, _ = await _setup(db_session, "gw-off@example.com", enable=False)
    gateway = BrokerSafetyGateway(db_session, user, get_settings())
    result = await gateway.execute(
        account=account,
        action=AutoTradeAction.OPEN,
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=Decimal("1"),
        stop_loss=Decimal("1"),
        take_profit=Decimal("10000"),
        confidence=Decimal("0.9"),
        idempotency_key="gw-off-1",
    )
    assert result.status == "REJECTED"
    assert result.reason == "AUTO_TRADING_DISABLED"
    assert await OrderRepository(db_session).count_for_account(account.id) == 0


async def test_auto_on_demo_open_executes(db_session) -> None:
    user, account, _ = await _setup(db_session, "gw-open@example.com")
    gateway = BrokerSafetyGateway(db_session, user, get_settings())
    result = await gateway.execute(
        account=account,
        action=AutoTradeAction.OPEN,
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=Decimal("1"),
        stop_loss=Decimal("1"),
        take_profit=Decimal("10000"),
        confidence=Decimal("0.9"),
        idempotency_key="gw-open-1",
    )
    assert result.status == "EXECUTED", result.reason
    assert result.order_id is not None
    assert result.environment == "DEMO"
    assert await OrderRepository(db_session).count_for_account(account.id) == 1


async def test_risk_rejection_blocks_order(db_session) -> None:
    user, account, _ = await _setup(db_session, "gw-risk@example.com")
    gateway = BrokerSafetyGateway(db_session, user, get_settings())
    # No stop loss: deterministic risk rules reject (require_stop_loss).
    result = await gateway.execute(
        account=account,
        action=AutoTradeAction.OPEN,
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=Decimal("1"),
        confidence=Decimal("0.9"),
        idempotency_key="gw-risk-1",
    )
    assert result.status == "REJECTED"
    assert result.reason and result.reason.startswith("RISK_REJECTED")
    assert await OrderRepository(db_session).count_for_account(account.id) == 0


async def test_emergency_stop_blocks_execution(db_session) -> None:
    user, account, _ = await _setup(db_session, "gw-estop@example.com")
    await TradingStateService(db_session, settings=get_settings()).transition(
        TradingState.EMERGENCY_STOP, reason="test", actor="tester"
    )
    gateway = BrokerSafetyGateway(db_session, user, get_settings())
    result = await gateway.execute(
        account=account,
        action=AutoTradeAction.OPEN,
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=Decimal("1"),
        stop_loss=Decimal("1"),
        take_profit=Decimal("10000"),
        confidence=Decimal("0.9"),
        idempotency_key="gw-estop-1",
    )
    assert result.status == "REJECTED"
    assert result.reason == "TRADING_STATE"
    assert await OrderRepository(db_session).count_for_account(account.id) == 0


async def test_reduce_and_close_flow(db_session) -> None:
    user, account, _ = await _setup(db_session, "gw-reduce@example.com")
    gateway = BrokerSafetyGateway(db_session, user, get_settings())
    opened = await gateway.execute(
        account=account,
        action=AutoTradeAction.OPEN,
        symbol="AAPL",
        side=TradeSide.BUY,
        quantity=Decimal("4"),
        stop_loss=Decimal("1"),
        take_profit=Decimal("10000"),
        confidence=Decimal("0.9"),
        idempotency_key="gw-reduce-open",
    )
    assert opened.status == "EXECUTED", opened.reason

    reduced = await gateway.execute(
        account=account,
        action=AutoTradeAction.REDUCE,
        symbol="AAPL",
        percent=Decimal("50"),
        idempotency_key="gw-reduce-1",
    )
    assert reduced.status == "EXECUTED", reduced.reason

    closed = await gateway.execute(
        account=account,
        action=AutoTradeAction.CLOSE,
        symbol="AAPL",
        idempotency_key="gw-close-1",
    )
    assert closed.status == "EXECUTED", closed.reason

    # No position left; a further close is rejected.
    again = await gateway.execute(
        account=account,
        action=AutoTradeAction.CLOSE,
        symbol="AAPL",
        idempotency_key="gw-close-2",
    )
    assert again.status == "REJECTED" and again.reason == "NO_POSITION"


async def test_cancel_requires_permission(db_session) -> None:
    from app.brokers.router import BrokerRouter
    from app.brokers.types import BrokerOrderRequest
    from app.models.enums import OrderType

    user, account, _ = await _setup(db_session, "gw-cancel@example.com")
    gateway = BrokerSafetyGateway(db_session, user, get_settings())

    # Rest a manual LIMIT order far from market via the broker adapter.
    broker = await BrokerRouter(db_session, get_settings()).route(user=user, account=account)
    submitted = await broker.submit_order(
        BrokerOrderRequest(
            symbol="AAPL",
            side=TradeSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1"),
            limit_price=Decimal("1"),
            idempotency_key="gw-rest-1",
        )
    )
    order_id = submitted.order_id

    denied = await gateway.cancel_order(account=account, order_id=order_id)
    assert denied.status == "REJECTED"
    assert denied.reason == "ACTION_NOT_PERMITTED:CANCEL_ORDER"

    service = AutoTradingPolicyService(db_session, get_settings())
    policy = await service.get_or_create(user.id, account)
    await service.update(policy, allow_cancel=True, allow_manage_manual_orders=True)
    cancelled = await gateway.cancel_order(account=account, order_id=order_id)
    assert cancelled.status == "EXECUTED", cancelled.reason


@pytest.mark.parametrize("symbol", ["BTC/USD"])
async def test_asset_class_restriction(db_session, symbol: str) -> None:
    user, account, _ = await _setup(db_session, f"gw-asset-{symbol.replace('/', '')}@example.com")
    policy = await AutoTradingPolicyService(db_session, get_settings()).get_or_create(
        user.id, account
    )
    await AutoTradingPolicyService(db_session, get_settings()).update(
        policy, allowed_asset_classes=["EQUITY"]
    )
    gateway = BrokerSafetyGateway(db_session, user, get_settings())
    result = await gateway.execute(
        account=account,
        action=AutoTradeAction.OPEN,
        symbol=symbol,
        side=TradeSide.BUY,
        quantity=Decimal("1"),
        stop_loss=Decimal("1"),
        take_profit=Decimal("10000"),
        confidence=Decimal("0.9"),
        idempotency_key="gw-asset-1",
    )
    assert result.status == "REJECTED"
    assert result.reason == "ASSET_CLASS_NOT_ALLOWED"
