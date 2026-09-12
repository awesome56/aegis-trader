"""Fixtures for market-data tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.core.config import Settings
from app.market.providers.mock import MockMarketDataProvider
from app.market.services.cache import InMemoryCacheBackend, MarketDataCache
from app.market.services.freshness import MarketDataFreshnessService
from app.market.services.market_data import MarketDataService

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
CSV_DIR = FIXTURES_DIR / "csv"
CSV_SINGLE_FILE = FIXTURES_DIR / "csv_single" / "combined.csv"

# A fixed instant exactly on an hour boundary, so mock candles align predictably.
FIXED_NOW = datetime(2026, 1, 15, 15, 0, 0, tzinfo=UTC)


def make_market_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "ENVIRONMENT": "test",
        "MARKET_DATA_PROVIDER": "mock",
        "MOCK_MARKET_SEED": 1234,
        "MOCK_MARKET_SYMBOLS": "AAPL,MSFT,NVDA",
        "MOCK_MARKET_START_PRICE": 100.0,
        "MOCK_MARKET_VOLATILITY": 0.02,
        "MOCK_MARKET_IS_OPEN": True,
        "MARKET_QUOTE_CACHE_TTL_SECONDS": 5,
        "MARKET_CANDLE_CACHE_TTL_SECONDS": 60,
        "MARKET_STATUS_CACHE_TTL_SECONDS": 30,
        "MAX_QUOTE_AGE_SECONDS": 900,
        "MAX_INTRADAY_CANDLE_AGE_SECONDS": 900,
        "MAX_DAILY_CANDLE_AGE_SECONDS": 86400,
        "MARKET_MAX_CANDLE_LIMIT": 1000,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


@pytest.fixture
def market_settings() -> Settings:
    return make_market_settings()


@pytest.fixture
def fixed_clock() -> Callable[[], datetime]:
    return lambda: FIXED_NOW


@pytest.fixture
def mock_provider(
    market_settings: Settings, fixed_clock: Callable[[], datetime]
) -> MockMarketDataProvider:
    return MockMarketDataProvider(market_settings, clock=fixed_clock)


@pytest.fixture
def memory_cache(market_settings: Settings) -> MarketDataCache:
    return MarketDataCache(backend=InMemoryCacheBackend(), settings=market_settings)


@pytest.fixture
def freshness(
    market_settings: Settings, fixed_clock: Callable[[], datetime]
) -> MarketDataFreshnessService:
    return MarketDataFreshnessService(market_settings, clock=fixed_clock)


@pytest.fixture
def market_service(
    db_session,  # noqa: ANN001
    mock_provider: MockMarketDataProvider,
    memory_cache: MarketDataCache,
    freshness: MarketDataFreshnessService,
    market_settings: Settings,
) -> MarketDataService:
    return MarketDataService(
        db_session,
        provider=mock_provider,
        cache=memory_cache,
        freshness=freshness,
        settings=market_settings,
    )
