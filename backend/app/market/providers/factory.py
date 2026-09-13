"""Provider factory. Provider selection is configuration-driven; application
services never import concrete providers directly.
"""

from __future__ import annotations

from collections.abc import Callable

from app.core.config import Settings, get_settings
from app.market.exceptions import ProviderUnavailableError
from app.market.providers.base import MarketDataProvider
from app.market.providers.csv import CsvMarketDataProvider
from app.market.providers.kraken import KrakenProvider
from app.market.providers.mock import MockMarketDataProvider
from app.market.providers.twelve_data import TwelveDataProvider

_PROVIDER_FACTORIES: dict[str, Callable[[Settings], MarketDataProvider]] = {
    MockMarketDataProvider.name: MockMarketDataProvider,
    CsvMarketDataProvider.name: CsvMarketDataProvider,
    TwelveDataProvider.name: TwelveDataProvider,
    KrakenProvider.name: KrakenProvider,
}

_providers: dict[str, MarketDataProvider] = {}


def get_market_data_provider(settings: Settings | None = None) -> MarketDataProvider:
    """Return the configured provider, memoised per provider name."""
    settings = settings or get_settings()
    name = settings.MARKET_DATA_PROVIDER.strip().lower()
    factory = _PROVIDER_FACTORIES.get(name)
    if factory is None:
        supported = ", ".join(sorted(_PROVIDER_FACTORIES))
        raise ProviderUnavailableError(
            f"Unsupported MARKET_DATA_PROVIDER {name!r}. Supported: {supported}",
            details={"supported": sorted(_PROVIDER_FACTORIES)},
        )
    if name not in _providers:
        _providers[name] = factory(settings)
    return _providers[name]


def reset_market_data_provider() -> None:
    """Clear the memoised providers (used by tests and on settings reload)."""
    _providers.clear()
