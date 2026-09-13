"""Provider factory. Provider selection is configuration-driven; application
services never import concrete providers directly.
"""

from __future__ import annotations

from collections.abc import Callable

from app.core.config import Settings, get_settings
from app.market.exceptions import ProviderUnavailableError
from app.market.providers.base import MarketDataProvider
from app.market.providers.composite import CompositeMarketDataProvider
from app.market.providers.csv import CsvMarketDataProvider
from app.market.providers.kraken import KrakenProvider
from app.market.providers.mock import MockMarketDataProvider
from app.market.providers.twelve_data import TwelveDataProvider

_PROVIDER_FACTORIES: dict[str, Callable[[Settings], MarketDataProvider]] = {
    MockMarketDataProvider.name: MockMarketDataProvider,
    CsvMarketDataProvider.name: CsvMarketDataProvider,
    TwelveDataProvider.name: TwelveDataProvider,
    KrakenProvider.name: KrakenProvider,
    CompositeMarketDataProvider.name: CompositeMarketDataProvider,
}

_providers: dict[str, MarketDataProvider] = {}


def create_provider_by_name(name: str, settings: Settings | None = None) -> MarketDataProvider:
    """Build a provider instance without memoisation (used by the composite)."""
    settings = settings or get_settings()
    key = name.strip().lower()
    factory = _PROVIDER_FACTORIES.get(key)
    if factory is None:
        supported = ", ".join(sorted(_PROVIDER_FACTORIES))
        raise ProviderUnavailableError(
            f"Unsupported MARKET_DATA_PROVIDER {name!r}. Supported: {supported}",
            details={"supported": sorted(_PROVIDER_FACTORIES)},
        )
    return factory(settings)


def get_market_data_provider(settings: Settings | None = None) -> MarketDataProvider:
    """Return the configured provider, memoised per provider name."""
    settings = settings or get_settings()
    name = settings.MARKET_DATA_PROVIDER.strip().lower()
    if name not in _PROVIDER_FACTORIES:
        supported = ", ".join(sorted(_PROVIDER_FACTORIES))
        raise ProviderUnavailableError(
            f"Unsupported MARKET_DATA_PROVIDER {name!r}. Supported: {supported}",
            details={"supported": sorted(_PROVIDER_FACTORIES)},
        )
    if name not in _providers:
        _providers[name] = create_provider_by_name(name, settings)
    return _providers[name]


def reset_market_data_provider() -> None:
    """Clear the memoised providers (used by tests and on settings reload)."""
    _providers.clear()
