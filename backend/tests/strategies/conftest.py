"""Fixtures and a fixed market-data provider for strategy tests."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from app.core.config import Settings
from app.market.domain.models import (
    AssetSearchResult,
    Candle,
    MarketQuote,
    MarketStatus,
    ProviderHealth,
)
from app.market.enums import MarketSession, ProviderStatus, Timeframe
from app.market.providers.base import MarketDataProvider
from app.market.services.cache import InMemoryCacheBackend, MarketDataCache
from app.market.services.freshness import MarketDataFreshnessService
from app.market.services.market_data import MarketDataService
from app.strategies.regime import MarketRegimeService
from app.strategies.service import StrategyService
from app.strategies.types import StrategyContext

from tests.brokers.conftest import broker_settings
from tests.strategies.helpers import (
    FIXED_NOW,
    build_candles,
    build_context,
    build_quote,
)


def strategy_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        # Generous regime thresholds keep synthetic tests on the NORMAL band
        # unless a test explicitly targets volatility regimes.
        "REGIME_HIGH_VOLATILITY_ATR_PERCENT": 50.0,
        "REGIME_LOW_VOLATILITY_ATR_PERCENT": 0.5,
        "REGIME_TREND_MIN_SPREAD_BPS": 5.0,
        "STRATEGY_TREND_MIN_MA_SPREAD_BPS": 5.0,
        "STRATEGY_TREND_MIN_CONFIDENCE": 0.4,
        "STRATEGY_MOMENTUM_MIN_CONFIDENCE": 0.4,
        "STRATEGY_MOMENTUM_MIN_RELATIVE_VOLUME": 0.8,
        "STRATEGY_MEAN_REVERSION_MIN_CONFIDENCE": 0.4,
        "STRATEGY_ANALYSIS_MAX_AGE_MULTIPLIER": 1000.0,
        "MARKET_QUOTE_CACHE_TTL_SECONDS": 0,
        "MARKET_CANDLE_CACHE_TTL_SECONDS": 0,
        "MARKET_MAX_CANDLE_LIMIT": 1000,
    }
    defaults.update(overrides)
    return broker_settings(**defaults)


class FixedMarketProvider(MarketDataProvider):
    """Returns a fixed candle series for deterministic strategy/service tests."""

    name = "fixed"

    def __init__(
        self,
        candles: list[Candle],
        *,
        now: datetime = FIXED_NOW,
    ) -> None:
        self._candles = candles
        self._now = now

    async def get_quote(self, symbol: str) -> MarketQuote:
        return build_quote(float(self._candles[-1].close), timestamp=self._now)

    async def get_quotes(self, symbols: list[str]) -> list[MarketQuote]:
        return [await self.get_quote(symbol) for symbol in symbols]

    async def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        limit: int | None = None,
    ) -> list[Candle]:
        selected = [c for c in self._candles if start <= c.open_time <= end]
        return selected[-limit:] if limit else selected

    async def get_latest_candles(
        self, symbol: str, timeframe: Timeframe, limit: int
    ) -> list[Candle]:
        return self._candles[-limit:]

    async def get_market_status(self) -> MarketStatus:
        return MarketStatus(
            is_open=True, session=MarketSession.REGULAR, timestamp=self._now, provider=self.name
        )

    async def search_assets(self, query: str) -> list[AssetSearchResult]:
        return []

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name, status=ProviderStatus.CONNECTED, checked_at=self._now
        )


@pytest.fixture
def settings_factory():
    return strategy_settings


@pytest.fixture
def regime_service() -> MarketRegimeService:
    return MarketRegimeService(strategy_settings())


@pytest_asyncio.fixture
async def strategy_env(db_session: Any) -> Any:
    """Build a StrategyService over a fixed candle series (all strategies enabled)."""

    async def _build(
        closes: list[float],
        *,
        volumes: list[int] | None = None,
        data_now: datetime = FIXED_NOW,
        clock_now: datetime | None = None,
        **overrides: object,
    ) -> SimpleNamespace:
        settings = strategy_settings(**overrides)
        effective_clock = clock_now or data_now
        candles = build_candles(closes, volumes=volumes, end=data_now)
        provider = FixedMarketProvider(candles, now=data_now)
        cache = MarketDataCache(backend=InMemoryCacheBackend(), settings=settings)
        freshness = MarketDataFreshnessService(settings, clock=lambda: effective_clock)
        market = MarketDataService(
            db_session, provider=provider, cache=cache, freshness=freshness, settings=settings
        )
        service = StrategyService(
            db_session, market, settings=settings, clock=lambda: effective_clock
        )
        await service.ensure_bootstrapped()
        for strategy in await service.list_strategies():
            strategy.is_enabled = True
        await db_session.flush()
        return SimpleNamespace(
            settings=settings,
            market=market,
            service=service,
            provider=provider,
            session=db_session,
            now=effective_clock,
        )

    return _build


def uptrend(count: int = 80, start: float = 100.0, step: float = 0.6) -> list[float]:
    return [start + step * index for index in range(count)]


def downtrend(count: int = 80, start: float = 160.0, step: float = 0.6) -> list[float]:
    return [start - step * index for index in range(count)]


def sideways(count: int = 80, base: float = 100.0, amplitude: float = 0.3) -> list[float]:
    return [base + amplitude * (index % 2) for index in range(count)]


def choppy_uptrend(count: int = 140) -> list[float]:
    import math

    return [
        100 + 0.06 * i + 0.5 * math.sin(i / 2.2) + 0.2 * math.cos(i / 1.1) for i in range(count)
    ]


def choppy_downtrend(count: int = 140) -> list[float]:
    import math

    return [
        140 - 0.06 * i - 0.5 * math.sin(i / 2.2) - 0.2 * math.cos(i / 1.1) for i in range(count)
    ]


def spike_down() -> list[float]:
    return [100.0] * 60 + [99.5, 99.0, 98.4, 97.8, 97.2, 96.6, 96.0]


def spike_up() -> list[float]:
    return [100.0] * 60 + [100.5, 101.0, 101.6, 102.2, 102.8, 103.4, 104.0]


def inside_bands(count: int = 70) -> list[float]:
    import math

    return [100 + 0.6 * math.sin(i / 2.0) for i in range(count)]


def context_for(closes: list[float], settings: Settings, **kwargs: Any) -> StrategyContext:
    return build_context(closes, MarketRegimeService(settings), **kwargs)
