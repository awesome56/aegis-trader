"""Fixtures for portfolio tests (reuse broker fixtures/settings)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest_asyncio
from app.brokers.bootstrap import ensure_paper_account
from app.brokers.paper import PaperBrokerAdapter
from app.market.providers.mock import MockMarketDataProvider
from app.market.services.cache import InMemoryCacheBackend, MarketDataCache
from app.market.services.freshness import MarketDataFreshnessService
from app.market.services.market_data import MarketDataService
from app.models.user import User
from app.portfolio.service import PortfolioService

from tests.brokers.conftest import FIXED_NOW, broker_settings


@pytest_asyncio.fixture
async def portfolio_env(db_session: Any) -> Callable[..., Any]:
    async def _build(**overrides: object) -> SimpleNamespace:
        settings = broker_settings(**overrides)
        clock: list = [FIXED_NOW]
        provider = MockMarketDataProvider(settings, clock=lambda: clock[0])
        cache = MarketDataCache(backend=InMemoryCacheBackend(), settings=settings)
        freshness = MarketDataFreshnessService(settings, clock=lambda: FIXED_NOW)
        market = MarketDataService(
            db_session, provider=provider, cache=cache, freshness=freshness, settings=settings
        )
        user = User(
            email=f"portfolio-{uuid.uuid4().hex[:10]}@example.com",
            hashed_password="x",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        account, portfolio = await ensure_paper_account(db_session, user, settings)
        broker = PaperBrokerAdapter(db_session, account, portfolio, market, settings=settings)
        service = PortfolioService(
            db_session,
            portfolio,
            market,
            account=account,
            settings=settings,
            clock=lambda: FIXED_NOW,
        )
        return SimpleNamespace(
            settings=settings,
            market=market,
            user=user,
            account=account,
            portfolio=portfolio,
            broker=broker,
            service=service,
            session=db_session,
            clock=clock,
        )

    return _build
