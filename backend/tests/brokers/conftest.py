"""Fixtures for broker tests."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest_asyncio
from app.brokers.bootstrap import ensure_paper_account
from app.brokers.paper import PaperBrokerAdapter
from app.core.config import Settings
from app.market.providers.mock import MockMarketDataProvider
from app.market.services.cache import InMemoryCacheBackend, MarketDataCache
from app.market.services.freshness import MarketDataFreshnessService
from app.market.services.market_data import MarketDataService
from app.models.user import User

FIXED_NOW = datetime(2026, 1, 15, 15, 0, 0, tzinfo=UTC)


def broker_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "ENVIRONMENT": "test",
        "MARKET_DATA_PROVIDER": "mock",
        "MOCK_MARKET_SEED": 7,
        "MOCK_MARKET_SYMBOLS": "AAPL,MSFT,NVDA",
        "MOCK_MARKET_START_PRICE": 100.0,
        "MOCK_MARKET_VOLATILITY": 0.02,
        "MOCK_MARKET_IS_OPEN": True,
        "MARKET_QUOTE_CACHE_TTL_SECONDS": 0,
        "MARKET_CANDLE_CACHE_TTL_SECONDS": 0,
        "MARKET_STATUS_CACHE_TTL_SECONDS": 30,
        "MAX_QUOTE_AGE_SECONDS": 900,
        "MAX_INTRADAY_CANDLE_AGE_SECONDS": 900,
        "MAX_DAILY_CANDLE_AGE_SECONDS": 86400,
        "MARKET_MAX_CANDLE_LIMIT": 1000,
        "BROKER_PROVIDER": "paper",
        "BROKER_PAPER_COMMISSION": 0.0,
        "BROKER_PAPER_SLIPPAGE_BPS": 0.0,
        "BROKER_PAPER_SPREAD_BPS": 1.0,
        "BROKER_PAPER_PARTIAL_FILLS": False,
        "BROKER_PAPER_PARTIAL_FILL_RATIO": 0.5,
        "BROKER_PAPER_AUTO_CREATE_ACCOUNT": True,
        "BROKER_PAPER_DEFAULT_CURRENCY": "USD",
        "PAPER_INITIAL_BALANCE": 100_000.0,
        "PORTFOLIO_SNAPSHOT_INTERVAL_SECONDS": 300,
        "PORTFOLIO_HISTORY_MAX_POINTS": 1000,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


@pytest_asyncio.fixture
async def broker_env(db_session: Any) -> Callable[..., Any]:
    """Build an isolated paper broker environment with optional overrides."""

    async def _build(
        *,
        provider_now: datetime = FIXED_NOW,
        freshness_now: datetime = FIXED_NOW,
        **overrides: object,
    ) -> SimpleNamespace:
        settings = broker_settings(**overrides)
        clock: list[datetime] = [provider_now]
        provider = MockMarketDataProvider(settings, clock=lambda: clock[0])
        cache = MarketDataCache(backend=InMemoryCacheBackend(), settings=settings)
        freshness = MarketDataFreshnessService(settings, clock=lambda: freshness_now)
        market = MarketDataService(
            db_session, provider=provider, cache=cache, freshness=freshness, settings=settings
        )
        user = User(
            email=f"broker-{uuid.uuid4().hex[:10]}@example.com",
            hashed_password="x",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        account, portfolio = await ensure_paper_account(db_session, user, settings)
        broker = PaperBrokerAdapter(db_session, account, portfolio, market, settings=settings)
        return SimpleNamespace(
            settings=settings,
            market=market,
            user=user,
            account=account,
            portfolio=portfolio,
            broker=broker,
            session=db_session,
            clock=clock,
        )

    return _build
