"""Broker provider selection.

V1 supports only the paper broker. Any real provider is refused unless the full
live-trading interlock is satisfied — configuration never silently falls back to
paper mode.
"""

from __future__ import annotations

from app.brokers.exceptions import BrokerConfigurationError
from app.core.config import Settings, get_settings

PAPER_PROVIDER = "paper"
# Providers that would require real money / live credentials.
LIVE_PROVIDERS = frozenset(
    {
        "alpaca",
        "interactive_brokers",
        "ibkr",
        "live",
        "tradier",
        "tiger",
        "webull",
        "coinbase",
        "binance",
        "kraken",
    }
)


def resolve_broker_provider(settings: Settings | None = None) -> str:
    """Return the validated provider name or raise a clear configuration error."""
    settings = settings or get_settings()
    provider = settings.BROKER_PROVIDER.strip().lower()

    if provider == PAPER_PROVIDER:
        return provider

    allowed, missing = settings.live_trading_allowed()
    if provider in LIVE_PROVIDERS or provider not in {PAPER_PROVIDER}:
        if not allowed:
            raise BrokerConfigurationError(
                f"Broker provider {provider!r} is not available in V1 and the live-trading "
                "interlock is locked.",
                details={"provider": provider, "missing_requirements": missing},
            )
        raise BrokerConfigurationError(
            f"Broker provider {provider!r} is not implemented yet.",
            details={"provider": provider},
        )

    return provider
