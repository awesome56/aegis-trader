"""Phase 10: broker connections, auto-trading policy, router (demo-first, fail-closed)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.auto_trading.service import AutoTradingPolicyService
from app.brokers.bootstrap import ensure_paper_account
from app.brokers.connections import BrokerConnectionService
from app.brokers.exceptions import BrokerConfigurationError
from app.brokers.paper import PaperBrokerAdapter
from app.brokers.router import BrokerRouter
from app.core.config import get_settings
from app.core.exceptions import ConflictError, ValidationError
from app.models.broker import BrokerAccount
from app.models.enums import AutoTradeAction, BrokerEnvironment, BrokerMode, ProviderStatus
from app.models.user import User
from app.repositories.broker_account import BrokerAccountRepository
from app.repositories.portfolio import PortfolioRepository
from httpx import AsyncClient

RAW_KEY = "demo-broker-secret-9876"


async def _user(session, email: str = "p10@example.com") -> User:
    user = User(email=email, hashed_password="x", is_active=True)
    session.add(user)
    await session.flush()
    return user


# --- connections ------------------------------------------------------------


async def test_connection_encrypts_and_never_returns_secret(db_session) -> None:
    from app.ai.security import get_cipher

    user = await _user(db_session)
    service = BrokerConnectionService(db_session)
    row = await service.create(
        user_id=user.id,
        provider="paper",
        environment=BrokerEnvironment.DEMO,
        api_key=RAW_KEY,
    )
    assert row.encrypted_api_key != RAW_KEY
    assert RAW_KEY not in (row.encrypted_api_key or "")
    assert get_cipher().decrypt(row.encrypted_api_key or "") == RAW_KEY
    assert service.masked(row) == "••••••9876"
    ok, status, _ = await service.test(row)
    assert ok is True and status == ProviderStatus.CONNECTED.value


async def test_live_connection_requires_server_interlock(db_session) -> None:
    user = await _user(db_session, "p10-live@example.com")
    service = BrokerConnectionService(db_session)
    with pytest.raises(ConflictError):
        await service.create(
            user_id=user.id,
            provider="alpaca",
            environment=BrokerEnvironment.LIVE,
            api_key=RAW_KEY,
        )


async def test_alpaca_connection_test_reaches_provider_with_stored_credentials(
    db_session, monkeypatch
) -> None:
    user = await _user(db_session, "p10-alpaca-ok@example.com")
    service = BrokerConnectionService(db_session)
    row = await service.create(
        user_id=user.id,
        provider="alpaca",
        environment=BrokerEnvironment.DEMO,
        api_key=RAW_KEY,
        api_secret="super-secret",
    )
    captured: dict[str, object] = {}

    class FakeAlpacaClient:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        async def get_account(self) -> dict[str, str]:
            return {"account_number": "PA3OK"}

        async def aclose(self) -> None:
            captured["closed"] = True

    monkeypatch.setattr("app.brokers.alpaca.client.AlpacaClient", FakeAlpacaClient)
    ok, status, _ = await service.test(row)
    assert ok is True and status == ProviderStatus.CONNECTED.value
    assert row.account_external_id == "PA3OK"
    assert captured["api_key"] == RAW_KEY
    assert captured["api_secret"] == "super-secret"
    assert captured["closed"] is True


async def test_alpaca_test_fails_closed_without_secret(db_session) -> None:
    user = await _user(db_session, "p10-alpaca-nosecret@example.com")
    service = BrokerConnectionService(db_session)
    row = await service.create(
        user_id=user.id,
        provider="alpaca",
        environment=BrokerEnvironment.DEMO,
        api_key=RAW_KEY,
    )
    ok, status, _ = await service.test(row)
    assert ok is False and status == ProviderStatus.ERROR.value


async def test_unimplemented_provider_fails_closed(db_session) -> None:
    user = await _user(db_session, "p10-oanda@example.com")
    service = BrokerConnectionService(db_session)
    row = await service.create(
        user_id=user.id,
        provider="oanda",
        environment=BrokerEnvironment.DEMO,
        api_key=RAW_KEY,
    )
    ok, status, _ = await service.test(row)
    assert ok is False and status == ProviderStatus.ERROR.value


async def test_connection_provisions_account_and_own_portfolio(db_session) -> None:
    user = await _user(db_session, "p10-provision@example.com")
    service = BrokerConnectionService(db_session)
    await service.create(
        user_id=user.id,
        provider="alpaca",
        environment=BrokerEnvironment.DEMO,
        api_key=RAW_KEY,
        api_secret="secret",
    )
    accounts = BrokerAccountRepository(db_session)
    account = await accounts.get_for_provider(
        user.id, broker="alpaca", environment=BrokerEnvironment.DEMO
    )
    assert account is not None
    assert account.mode is BrokerMode.PAPER
    assert account.is_active is True

    portfolio = await PortfolioRepository(db_session).get_for_broker_account(account.id)
    assert portfolio is not None
    # External accounts never share the paper portfolio the UI treats as default.
    assert portfolio.is_default is False

    # Idempotent: another connection for the same provider/env reuses the account.
    await service.create(
        user_id=user.id,
        provider="alpaca",
        environment=BrokerEnvironment.DEMO,
        api_key=RAW_KEY,
        api_secret="secret",
    )
    alpaca_accounts = [
        row for row in await accounts.list_for_user(user.id) if row.broker == "alpaca"
    ]
    assert len(alpaca_accounts) == 1


async def test_paper_connection_does_not_provision_a_second_account(db_session) -> None:
    user = await _user(db_session, "p10-provision-paper@example.com")
    await ensure_paper_account(db_session, user)
    service = BrokerConnectionService(db_session)
    await service.create(
        user_id=user.id,
        provider="paper",
        environment=BrokerEnvironment.DEMO,
        api_key=RAW_KEY,
    )
    paper_accounts = [
        row
        for row in await BrokerAccountRepository(db_session).list_for_user(user.id)
        if row.broker == "paper"
    ]
    assert len(paper_accounts) == 1


# --- policy -----------------------------------------------------------------


async def test_policy_defaults_conservative_and_demo_live_independent(db_session) -> None:
    user = await _user(db_session, "p10-policy@example.com")
    _, demo = await ensure_paper_account(db_session, user)
    account = await db_session.get(BrokerAccount, demo.broker_account_id)
    service = AutoTradingPolicyService(db_session)
    policy = await service.get_or_create(user.id, account)
    assert policy.enabled is False
    assert policy.allow_add is False and policy.allow_cancel is False
    assert service.allowed_actions(policy) == set()

    with pytest.raises(ValidationError):
        await service.enable(user.id, policy, confirm=False)
    enabled = await service.enable(user.id, policy, confirm=True)
    assert enabled.enabled is True
    assert AutoTradeAction.OPEN in service.allowed_actions(enabled)
    assert AutoTradeAction.ADD not in service.allowed_actions(enabled)

    ok, reason = service.permits(enabled, AutoTradeAction.ADD)
    assert ok is False and reason == "ACTION_NOT_PERMITTED:ADD"


async def test_live_policy_enable_blocked_without_interlock(db_session) -> None:
    user = await _user(db_session, "p10-livepolicy@example.com")
    now = __import__("datetime").datetime.now(__import__("datetime").UTC)
    account = BrokerAccount(
        user_id=user.id,
        broker="paper",
        account_name="live-test",
        mode=BrokerMode.LIVE,
        environment=BrokerEnvironment.LIVE,
        cash_balance=Decimal("0"),
        buying_power=Decimal("0"),
        currency="USD",
        created_at=now,
        updated_at=now,
    )
    db_session.add(account)
    await db_session.flush()
    service = AutoTradingPolicyService(db_session)
    policy = await service.get_or_create(user.id, account)
    with pytest.raises(ConflictError):
        await service.enable(user.id, policy, confirm=True, phrase="ENABLE LIVE AUTO TRADING")


async def test_policy_restricts_asset_class_and_symbol(db_session) -> None:
    user = await _user(db_session, "p10-scope@example.com")
    _, portfolio = await ensure_paper_account(db_session, user)
    account = await db_session.get(BrokerAccount, portfolio.broker_account_id)
    service = AutoTradingPolicyService(db_session)
    policy = await service.get_or_create(user.id, account)
    policy = await service.enable(user.id, policy, confirm=True)
    policy = await service.update(
        policy, allowed_asset_classes=["CRYPTO"], allowed_symbols=["BTC/USD"]
    )
    assert service.permits(policy, AutoTradeAction.OPEN, asset_class="CRYPTO", symbol="BTC/USD")[0]
    assert not service.permits(policy, AutoTradeAction.OPEN, asset_class="EQUITY")[0]
    assert (
        service.permits(policy, AutoTradeAction.OPEN, asset_class="CRYPTO", symbol="ETH/USD")[1]
        == "SYMBOL_NOT_ALLOWED"
    )


# --- router -----------------------------------------------------------------


async def test_router_routes_paper_and_blocks_live_and_unknown(db_session) -> None:
    user = await _user(db_session, "p10-router@example.com")
    account, portfolio = await ensure_paper_account(db_session, user)
    router = BrokerRouter(db_session, get_settings())
    adapter = await router.route(user=user, account=account)
    assert isinstance(adapter, PaperBrokerAdapter)

    now = __import__("datetime").datetime.now(__import__("datetime").UTC)
    live = BrokerAccount(
        user_id=user.id,
        broker="paper",
        account_name="live",
        mode=BrokerMode.LIVE,
        environment=BrokerEnvironment.LIVE,
        cash_balance=Decimal("0"),
        buying_power=Decimal("0"),
        currency="USD",
        created_at=now,
        updated_at=now,
    )
    db_session.add(live)
    await db_session.flush()
    with pytest.raises(BrokerConfigurationError):
        await router.route(user=user, account=live)

    unknown = BrokerAccount(
        user_id=user.id,
        broker="alpaca",
        account_name="alpaca-demo",
        mode=BrokerMode.PAPER,
        environment=BrokerEnvironment.DEMO,
        cash_balance=Decimal("0"),
        buying_power=Decimal("0"),
        currency="USD",
        created_at=now,
        updated_at=now,
    )
    db_session.add(unknown)
    await db_session.flush()
    with pytest.raises(BrokerConfigurationError):
        await router.route(user=user, account=unknown)


# --- API --------------------------------------------------------------------


async def test_connections_api_masks_secret_and_status(authenticated_client: AsyncClient) -> None:
    created = await authenticated_client.post(
        "/api/v1/brokers/connections",
        json={"provider": "paper", "environment": "DEMO", "api_key": RAW_KEY},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["api_key_masked"] == "••••••9876"
    assert RAW_KEY not in created.text

    listed = await authenticated_client.get("/api/v1/brokers/connections")
    assert listed.status_code == 200 and RAW_KEY not in listed.text

    status = await authenticated_client.get("/api/v1/auto-trading/status")
    assert status.status_code == 200
    payload = status.json()
    assert payload["live_trading_allowed"] is False
    assert payload["demo_any_enabled"] is False and payload["live_any_enabled"] is False
    assert payload["accounts"]


async def test_auto_trading_enable_requires_confirm(authenticated_client: AsyncClient) -> None:
    status = (await authenticated_client.get("/api/v1/auto-trading/status")).json()
    account_id = status["accounts"][0]["broker_account_id"]
    bad = await authenticated_client.post(
        f"/api/v1/auto-trading/{account_id}/enable", json={"confirm": False}
    )
    assert bad.status_code == 422
    good = await authenticated_client.post(
        f"/api/v1/auto-trading/{account_id}/enable", json={"confirm": True}
    )
    assert good.status_code == 200 and good.json()["enabled"] is True
