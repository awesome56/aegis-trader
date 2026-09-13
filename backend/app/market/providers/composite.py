"""Composite provider: routes each symbol to a provider by asset class.

Lets the platform mix sources cleanly — e.g. mock equities (so existing paper
positions keep valuing) alongside a real crypto feed and a real forex feed —
without any strategy/agent code knowing which venue served the data.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from app.core.config import Settings, get_settings
from app.market.domain.models import (
    AssetSearchResult,
    Candle,
    MarketQuote,
    MarketStatus,
    ProviderHealth,
)
from app.market.enums import ProviderStatus, Timeframe
from app.market.exceptions import ProviderUnavailableError
from app.market.providers.base import MarketDataProvider
from app.market.validation import detect_asset_class
from app.models.enums import AssetClass


class CompositeMarketDataProvider(MarketDataProvider):
    name = "composite"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        providers: Mapping[AssetClass, MarketDataProvider] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        if providers is not None:
            self._providers = dict(providers)
        else:
            from app.market.providers.factory import create_provider_by_name

            equity = create_provider_by_name(self._settings.MARKET_EQUITY_PROVIDER, self._settings)
            crypto = create_provider_by_name(self._settings.MARKET_CRYPTO_PROVIDER, self._settings)
            forex = create_provider_by_name(self._settings.MARKET_FOREX_PROVIDER, self._settings)
            self._providers = {
                AssetClass.EQUITY: equity,
                AssetClass.ETF: equity,
                AssetClass.CRYPTO: crypto,
                AssetClass.FOREX: forex,
            }

    def provider_for(self, symbol: str) -> MarketDataProvider:
        asset_class = detect_asset_class(symbol)
        provider = self._providers.get(asset_class) or self._providers.get(AssetClass.EQUITY)
        if provider is None:
            raise KeyError(f"No provider configured for {asset_class}")
        return provider

    async def get_quote(self, symbol: str) -> MarketQuote:
        return await self.provider_for(symbol).get_quote(symbol)

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
        return await self.provider_for(symbol).get_candles(symbol, timeframe, start, end, limit)

    async def get_latest_candles(
        self, symbol: str, timeframe: Timeframe, limit: int
    ) -> list[Candle]:
        return await self.provider_for(symbol).get_latest_candles(symbol, timeframe, limit)

    async def get_market_status(self) -> MarketStatus:
        equities = self._providers.get(AssetClass.EQUITY)
        if equities is None:
            raise ProviderUnavailableError("no equity provider configured for market status")
        status = await equities.get_market_status()
        return status.model_copy(update={"provider": self.name})

    async def search_assets(self, query: str) -> list[AssetSearchResult]:
        seen: dict[str, AssetSearchResult] = {}
        for provider in {id(p): p for p in self._providers.values()}.values():
            try:
                for result in await provider.search_assets(query):
                    seen.setdefault(result.symbol, result)
            except Exception:  # noqa: BLE001, S112 - search is best-effort across venues
                continue
        return list(seen.values())

    async def health_check(self) -> ProviderHealth:
        reports: list[ProviderHealth] = []
        for provider in {id(p): p for p in self._providers.values()}.values():
            try:
                reports.append(await provider.health_check())
            except Exception as exc:  # noqa: BLE001 - health must never raise
                reports.append(
                    ProviderHealth(
                        provider=provider.name,
                        status=ProviderStatus.DISCONNECTED,
                        detail=str(exc),
                        checked_at=datetime.now(UTC),
                    )
                )
        connected = [
            r for r in reports if r.status in (ProviderStatus.CONNECTED, ProviderStatus.MOCK)
        ]
        if len(connected) == len(reports):
            status = ProviderStatus.CONNECTED
        elif connected:
            status = ProviderStatus.DEGRADED
        else:
            status = ProviderStatus.DISCONNECTED
        detail = ", ".join(f"{r.provider}:{r.status.value}" for r in reports)
        latency = max((r.latency_ms or 0.0) for r in reports) if reports else None
        return ProviderHealth(
            provider=self.name,
            status=status,
            latency_ms=latency,
            detail=detail,
            checked_at=datetime.now(UTC),
        )
