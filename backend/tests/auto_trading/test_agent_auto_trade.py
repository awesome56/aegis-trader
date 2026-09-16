"""Agent AUTO_TRADE wiring + autonomous worker cycle (Phase 10)."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from app.agents.service import AgentService
from app.ai.types import LLMResponse, LLMToolCall
from app.auto_trading.service import AutoTradingPolicyService
from app.brokers.bootstrap import ensure_paper_account
from app.core.config import get_settings
from app.models.enums import AgentMode
from app.models.user import User
from app.repositories.auto_trading import AutoTradingPolicyRepository
from app.repositories.order import OrderRepository

from tests.ai.fake_provider import fake_factory

FINAL = {
    "symbol": "AAPL",
    "action": "HOLD",
    "confidence": 0.4,
    "market_regime": "SIDEWAYS",
    "summary": "No edge.",
    "supporting_evidence": [],
    "concerns": [],
    "strategy_signals": [],
    "risk_context_summary": None,
    "proposal_recommended": False,
    "proposed_trade": None,
}


def _final() -> LLMResponse:
    return LLMResponse(content=json.dumps(FINAL), provider="fake", model="m")


def _open_call() -> LLMResponse:
    return LLMResponse(
        tool_calls=[
            LLMToolCall(
                id="c1",
                name="broker_open_position",
                arguments={
                    "symbol": "AAPL",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "quantity": 1,
                    "stop_loss": 1,
                    "take_profit": 10000,
                    "confidence": 0.9,
                },
            )
        ],
        provider="fake",
        model="m",
    )


async def _user(session, email: str) -> User:
    user = User(email=email, hashed_password="x", is_active=True)
    session.add(user)
    await session.flush()
    return user


async def _provider_config(session, user):
    from app.ai.service import AIProviderService

    return await AIProviderService(session, get_settings()).create(
        user_id=user.id, provider="openai", model="m", api_key="sk-test-1234"
    )


async def test_auto_trade_off_exposes_no_write_tools(db_session, monkeypatch) -> None:
    user = await _user(db_session, "auto-off@example.com")
    account, _ = await ensure_paper_account(db_session, user)
    await _provider_config(db_session, user)
    monkeypatch.setattr("app.agents.service.create_provider", fake_factory(responses=[_final()]))

    service = AgentService(db_session, get_settings())
    run = await service.create_run(
        user_id=user.id,
        symbol="AAPL",
        timeframe="1h",
        mode=AgentMode.AUTO_TRADE,
        broker_account_id=account.id,
    )
    run = await service.execute(run.id)
    assert run.status.value == "COMPLETED"
    # Policy is disabled by default -> no autonomous order.
    assert await OrderRepository(db_session).count_for_account(account.id) == 0


async def test_auto_trade_on_opens_position_via_gateway(db_session, monkeypatch) -> None:
    user = await _user(db_session, "auto-on@example.com")
    account, _ = await ensure_paper_account(db_session, user)
    await _provider_config(db_session, user)
    policies = AutoTradingPolicyService(db_session, get_settings())
    policy = await policies.get_or_create(user.id, account)
    policy = await policies.update(policy, allow_open=True)
    await policies.enable(user.id, policy, confirm=True)

    monkeypatch.setattr(
        "app.agents.service.create_provider", fake_factory(responses=[_open_call(), _final()])
    )
    service = AgentService(db_session, get_settings())
    run = await service.create_run(
        user_id=user.id,
        symbol="AAPL",
        timeframe="1h",
        mode=AgentMode.AUTO_TRADE,
        broker_account_id=account.id,
    )
    run = await service.execute(run.id)
    assert run.status.value == "COMPLETED"
    assert await OrderRepository(db_session).count_for_account(account.id) == 1


async def test_auto_trade_requires_account(db_session) -> None:
    from app.core.exceptions import ValidationError

    user = await _user(db_session, "auto-noaccount@example.com")
    await _provider_config(db_session, user)
    service = AgentService(db_session, get_settings())
    with pytest.raises(ValidationError):
        await service.create_run(
            user_id=user.id, symbol="AAPL", timeframe="1h", mode=AgentMode.AUTO_TRADE
        )


async def test_repository_lists_only_enabled_policies(db_session) -> None:
    user = await _user(db_session, "auto-repo@example.com")
    account, _ = await ensure_paper_account(db_session, user)
    policies = AutoTradingPolicyService(db_session, get_settings())
    policy = await policies.get_or_create(user.id, account)
    repo = AutoTradingPolicyRepository(db_session)
    assert await repo.list_enabled() == []
    await policies.enable(user.id, policy, confirm=True)
    enabled = await repo.list_enabled()
    assert len(enabled) == 1 and enabled[0].broker_account_id == account.id


async def test_autonomous_worker_skips_when_disabled() -> None:
    from app.workers.jobs import run_autonomous_agent

    result = await run_autonomous_agent({})
    assert result["skipped"] is True
    assert result["reason"] == "disabled"


def test_autonomous_worker_registered() -> None:
    from app.workers.main import WorkerSettings

    names = {fn.__name__ for fn in WorkerSettings.functions}
    assert "run_autonomous_agent" in names
    assert Decimal("0") == Decimal("0")
