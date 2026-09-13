"""Backtesting REST API tests (authenticated, owner-scoped)."""

from __future__ import annotations

import uuid

import pytest_asyncio
from app.core.config import get_settings
from app.database.session import get_session_factory
from app.models.market import MarketCandle
from app.repositories.strategy import StrategyRepository
from app.strategies.bootstrap import ensure_strategies
from httpx import AsyncClient
from sqlalchemy import delete

BASE = "/api/v1/backtests"


@pytest_asyncio.fixture(autouse=True)
async def _clean_market_cache():
    """API requests commit candles; remove them so later suites stay isolated."""
    yield
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(MarketCandle))
        await session.commit()


@pytest_asyncio.fixture
async def trend_strategy_id():
    factory = get_session_factory()
    async with factory() as session:
        await ensure_strategies(session, get_settings())
        await session.commit()
        strategy = await StrategyRepository(session).get_by_slug("trend_following")
        return strategy.id


def payload(strategy_id) -> dict:
    return {
        "strategy_id": str(strategy_id),
        "symbols": ["AAPL"],
        "timeframe": "1h",
        "start_date": "2026-01-01",
        "end_date": "2026-01-06",
        "initial_capital": "100000",
        "fees_pct": "0",
        "slippage_pct": "0",
    }


async def test_create_run_and_read(authenticated_client: AsyncClient, trend_strategy_id) -> None:
    created = await authenticated_client.post(BASE, json=payload(trend_strategy_id))
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "COMPLETED"
    assert body["symbols"] == ["AAPL"]
    backtest_id = body["id"]

    listed = await authenticated_client.get(BASE)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    detail = await authenticated_client.get(f"{BASE}/{backtest_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == backtest_id

    result = await authenticated_client.get(f"{BASE}/{backtest_id}/result")
    assert result.status_code == 200, result.text
    result_body = result.json()
    from decimal import Decimal

    assert Decimal(result_body["metrics"]["initial_capital"]) == Decimal("100000")
    assert result_body["engine_version"]
    assert isinstance(result_body["equity_curve"], list)
    assert result_body["equity_curve"]
    assert "drawdown_curve" in result_body


async def test_validation_rejects_bad_range(
    authenticated_client: AsyncClient, trend_strategy_id
) -> None:
    bad = payload(trend_strategy_id)
    bad["end_date"] = "2025-12-31"
    response = await authenticated_client.post(BASE, json=bad)
    assert response.status_code in (400, 422)


async def test_unknown_backtest_returns_404(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get(f"{BASE}/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_completed_backtest_cannot_be_cancelled(
    authenticated_client: AsyncClient, trend_strategy_id
) -> None:
    created = await authenticated_client.post(BASE, json=payload(trend_strategy_id))
    backtest_id = created.json()["id"]
    response = await authenticated_client.post(f"{BASE}/{backtest_id}/cancel")
    assert response.status_code == 409
