"""Provider-independent market-data subsystem (Phase 2).

Nothing here may import brokers, orders, agents, risk or portfolio execution.
Dependency direction is ``strategies -> market``, never the reverse.
"""

from app.market.enums import MarketSession, ProviderStatus, Timeframe
from app.market.exceptions import (
    AssetNotFoundError,
    InvalidMarketDataError,
    MarketClosedError,
    MarketDataError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    StaleMarketDataError,
    UnsupportedTimeframeError,
)
from app.market.validation import normalize_symbol, to_decimal

__all__ = [
    "AssetNotFoundError",
    "InvalidMarketDataError",
    "MarketClosedError",
    "MarketDataError",
    "MarketSession",
    "ProviderAuthenticationError",
    "ProviderRateLimitError",
    "ProviderStatus",
    "ProviderUnavailableError",
    "StaleMarketDataError",
    "Timeframe",
    "UnsupportedTimeframeError",
    "normalize_symbol",
    "to_decimal",
]
