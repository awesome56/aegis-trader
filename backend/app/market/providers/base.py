"""Abstract market-data provider interface.

Trading logic depends only on this interface. Provider SDKs and HTTP details stay
inside concrete implementations; provider exceptions are normalised in
``app.market.exceptions`` before they reach callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.market.domain.models import (
    AssetSearchResult,
    Candle,
    MarketQuote,
    MarketStatus,
    ProviderHealth,
)
from app.market.enums import Timeframe


class MarketDataProvider(ABC):
    """Provider contract. Not every provider must support every operation, but
    unsupported operations must raise a normalised market-data error rather than
    a provider-specific one.
    """

    name: str = "base"

    @abstractmethod
    async def get_quote(self, symbol: str) -> MarketQuote:
        """Return the latest quote for ``symbol``."""

    @abstractmethod
    async def get_quotes(self, symbols: list[str]) -> list[MarketQuote]:
        """Return latest quotes for several symbols."""

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        limit: int | None = None,
    ) -> list[Candle]:
        """Return historical candles in ``[start, end]`` ascending by open time."""

    @abstractmethod
    async def get_latest_candles(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int,
    ) -> list[Candle]:
        """Return the most recent ``limit`` candles ascending by open time."""

    @abstractmethod
    async def get_market_status(self) -> MarketStatus:
        """Return the current market session status."""

    @abstractmethod
    async def search_assets(self, query: str) -> list[AssetSearchResult]:
        """Search the provider's asset universe."""

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Return a cheap, normalised provider health report."""
