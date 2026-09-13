"""Composite provider routing tests (no network)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import get_settings
from app.market.domain.models import (
    AssetSearchResult,
    MarketQuote,
    MarketStatus,
    ProviderHealth,
)
from app.market.enums import MarketSession, ProviderStatus
from app.market.providers.base import MarketDataProvider
from app.market.providers.composite import CompositeMarketDataProvider
from app.market.providers.factory import create_provider_by_name
from app.market.validation import to_decimal
from app.models.enums import AssetClass


class FakeProvider(MarketDataProvider):
    def __init__(self, name: str, status: ProviderStatus = ProviderStatus.CONNECTED) -> None:
        self.name = name
        self._status = status
        self.seen: list[str] = []

    async def get_quote(self, symbol: str) -> MarketQuote:
        self.seen.append(symbol)
        return MarketQuote(
            symbol=symbol.upper(),
            last=to_decimal("100"),
            provider=self.name,
            market_timestamp=datetime.now(UTC),
            received_at=datetime.now(UTC),
        )

    async def get_quotes(self, symbols: list[str]) -> list[MarketQuote]:
        return [await self.get_quote(symbol) for symbol in symbols]

    async def get_candles(self, symbol, timeframe, start, end, limit=None):  # noqa: ANN001
        self.seen.append(symbol)
        return []

    async def get_latest_candles(self, symbol, timeframe, limit):  # noqa: ANN001
        self.seen.append(symbol)
        return []

    async def get_market_status(self) -> MarketStatus:
        return MarketStatus(
            market="EQUITIES",
            is_open=True,
            session=MarketSession.REGULAR,
            timestamp=datetime.now(UTC),
            provider=self.name,
        )

    async def search_assets(self, query: str) -> list[AssetSearchResult]:
        return []

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, status=self._status, checked_at=datetime.now(UTC))


def _composite(**status) -> tuple[CompositeMarketDataProvider, dict[str, FakeProvider]]:
    equity = FakeProvider("mock-equity", status.get("equity", ProviderStatus.CONNECTED))
    crypto = FakeProvider("kraken", status.get("crypto", ProviderStatus.CONNECTED))
    forex = FakeProvider("twelvedata", status.get("forex", ProviderStatus.CONNECTED))
    composite = CompositeMarketDataProvider(
        get_settings(),
        providers={
            AssetClass.EQUITY: equity,
            AssetClass.ETF: equity,
            AssetClass.CRYPTO: crypto,
            AssetClass.FOREX: forex,
        },
    )
    return composite, {"equity": equity, "crypto": crypto, "forex": forex}


async def test_routes_by_asset_class() -> None:
    composite, providers = _composite()
    await composite.get_quote("AAPL")
    await composite.get_quote("SPY")
    await composite.get_quote("BTC/USD")
    await composite.get_quote("EUR/USD")
    assert providers["equity"].seen == ["AAPL", "SPY"]
    assert providers["crypto"].seen == ["BTC/USD"]
    assert providers["forex"].seen == ["EUR/USD"]


async def test_health_aggregation() -> None:
    _, all_up = _composite()
    composite, _ = _composite()
    assert (await composite.health_check()).status is ProviderStatus.CONNECTED

    mixed, _ = _composite(crypto=ProviderStatus.DISCONNECTED)
    assert (await mixed.health_check()).status is ProviderStatus.DEGRADED

    down, _ = _composite(
        equity=ProviderStatus.DISCONNECTED,
        crypto=ProviderStatus.DISCONNECTED,
        forex=ProviderStatus.DISCONNECTED,
    )
    assert (await down.health_check()).status is ProviderStatus.DISCONNECTED
    assert all_up is not None


def test_factory_builds_composite() -> None:
    provider = create_provider_by_name("composite", get_settings())
    assert provider.name == "composite"
