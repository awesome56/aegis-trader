"""Normalised market-data exceptions.

External/provider errors must be translated into these types before they leave
the provider boundary. The API layer maps them to HTTP responses through the
existing :class:`~app.core.exceptions.AegisError` handler.
"""

from __future__ import annotations

from app.core.exceptions import AegisError


class MarketDataError(AegisError):
    """Base class for all market-data errors."""

    status_code = 502
    code = "market_data_error"


class ProviderUnavailableError(MarketDataError):
    status_code = 503
    code = "provider_unavailable"


class ProviderAuthenticationError(MarketDataError):
    status_code = 502
    code = "provider_authentication_error"


class ProviderRateLimitError(MarketDataError):
    status_code = 429
    code = "provider_rate_limit"


class AssetNotFoundError(MarketDataError):
    status_code = 404
    code = "asset_not_found"


class UnsupportedTimeframeError(MarketDataError):
    status_code = 422
    code = "unsupported_timeframe"


class InvalidMarketDataError(MarketDataError):
    """Provider returned data that violates market-data invariants."""

    status_code = 422
    code = "invalid_market_data"


class StaleMarketDataError(MarketDataError):
    """Market data is too old to be used for a trading decision (fail closed)."""

    status_code = 409
    code = "stale_market_data"


class MarketClosedError(MarketDataError):
    status_code = 409
    code = "market_closed"
