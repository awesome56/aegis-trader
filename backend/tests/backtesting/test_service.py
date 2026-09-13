"""Backtest service tests: persistence, ownership, determinism, no side effects."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from app.backtesting.service import BacktestService
from app.backtesting.types import ENGINE_VERSION
from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.market.providers.factory import reset_market_data_provider
from app.models.enums import BacktestStatus
from app.models.user import User
from app.repositories.order import OrderRepository
from app.repositories.proposal import TradeProposalRepository
from app.repositories.strategy import StrategyRepository
from app.strategies.bootstrap import ensure_strategies

START = date(2026, 1, 1)
END = date(2026, 1, 6)


@pytest.fixture(autouse=True)
def _reset_provider():
    reset_market_data_provider()
    yield
    reset_market_data_provider()


def scenario_settings(scenario: str):
    return get_settings().model_copy(
        update={
            "MOCK_MARKET_SCENARIO": scenario,
            "MARKET_CANDLE_CACHE_TTL_SECONDS": 0,
            "MARKET_QUOTE_CACHE_TTL_SECONDS": 0,
        }
    )


async def _user(session, email: str) -> User:
    user = User(email=email, hashed_password="x", is_active=True)
    session.add(user)
    await session.flush()
    return user


async def _strategy_id(session, settings) -> object:
    await ensure_strategies(session, settings)
    strategy = await StrategyRepository(session).get_by_slug("trend_following")
    assert strategy is not None
    return strategy.id


async def test_run_persists_result_and_is_deterministic(db_session) -> None:
    settings = scenario_settings("uptrend")
    user = await _user(db_session, "bt-owner@example.com")
    strategy_id = await _strategy_id(db_session, settings)
    service = BacktestService(db_session, settings)

    async def run_once():
        backtest = await service.create(
            user_id=user.id,
            strategy_id=strategy_id,
            symbols=["MSFT"],
            timeframe="1h",
            start_date=START,
            end_date=END,
            initial_capital=Decimal("100000"),
        )
        assert backtest.status is BacktestStatus.PENDING
        executed = await service.execute(backtest.id)
        assert executed.status is BacktestStatus.COMPLETED
        result = await service.result_for(backtest.id)
        assert result is not None
        return result

    first = await run_once()
    second = await run_once()
    assert first.num_trades >= 1
    assert first.engine_version == ENGINE_VERSION
    assert first.final_capital == second.final_capital
    assert first.total_return_pct == second.total_return_pct
    assert first.metrics is not None
    assert first.strategy_config is not None
    assert first.equity_curve
    assert first.monthly_returns


async def test_ownership_is_enforced(db_session) -> None:
    settings = scenario_settings("uptrend")
    owner = await _user(db_session, "bt-a@example.com")
    other = await _user(db_session, "bt-b@example.com")
    strategy_id = await _strategy_id(db_session, settings)
    service = BacktestService(db_session, settings)
    backtest = await service.create(
        user_id=owner.id,
        strategy_id=strategy_id,
        symbols=["MSFT"],
        timeframe="1h",
        start_date=START,
        end_date=END,
        initial_capital=Decimal("100000"),
    )
    with pytest.raises(NotFoundError):
        await service.get(other.id, backtest.id)


async def test_cancel_pending_only(db_session) -> None:
    settings = scenario_settings("uptrend")
    user = await _user(db_session, "bt-cancel@example.com")
    strategy_id = await _strategy_id(db_session, settings)
    service = BacktestService(db_session, settings)
    backtest = await service.create(
        user_id=user.id,
        strategy_id=strategy_id,
        symbols=["MSFT"],
        timeframe="1h",
        start_date=START,
        end_date=END,
        initial_capital=Decimal("100000"),
    )
    cancelled = await service.cancel(user.id, backtest.id)
    assert cancelled.status is BacktestStatus.CANCELLED

    completed = await service.create(
        user_id=user.id,
        strategy_id=strategy_id,
        symbols=["MSFT"],
        timeframe="1h",
        start_date=START,
        end_date=END,
        initial_capital=Decimal("100000"),
    )
    await service.execute(completed.id)
    with pytest.raises(ConflictError):
        await service.cancel(user.id, completed.id)


async def test_does_not_touch_live_trading_state(db_session) -> None:
    settings = scenario_settings("uptrend")
    user = await _user(db_session, "bt-safe@example.com")
    strategy_id = await _strategy_id(db_session, settings)
    service = BacktestService(db_session, settings)
    backtest = await service.create(
        user_id=user.id,
        strategy_id=strategy_id,
        symbols=["MSFT"],
        timeframe="1h",
        start_date=START,
        end_date=END,
        initial_capital=Decimal("100000"),
    )
    await service.execute(backtest.id)

    from app.brokers.bootstrap import ensure_paper_account

    account, portfolio = await ensure_paper_account(db_session, user, settings)
    assert await TradeProposalRepository(db_session).count_for_portfolio(portfolio.id) == 0
    assert await OrderRepository(db_session).count_for_account(account.id) == 0


async def test_create_validates_range_and_capital(db_session) -> None:
    settings = scenario_settings("uptrend")
    user = await _user(db_session, "bt-invalid@example.com")
    strategy_id = await _strategy_id(db_session, settings)
    service = BacktestService(db_session, settings)
    from app.backtesting.exceptions import BacktestValidationError

    with pytest.raises(BacktestValidationError):
        await service.create(
            user_id=user.id,
            strategy_id=strategy_id,
            symbols=["MSFT"],
            timeframe="1h",
            start_date=END,
            end_date=START,
            initial_capital=Decimal("100000"),
        )
    with pytest.raises(BacktestValidationError):
        await service.create(
            user_id=user.id,
            strategy_id=strategy_id,
            symbols=["MSFT"],
            timeframe="1h",
            start_date=START,
            end_date=END,
            initial_capital=Decimal("-1"),
        )


def test_engine_version_constant() -> None:
    assert ENGINE_VERSION == "phase8-v1"
    assert datetime.now(UTC).tzinfo is not None
