"""Alpaca broker adapter.

Stage A (this module) implements *reads* against the account's Alpaca endpoint:
account state, balances, positions, quotes and the market clock. Order routing
is deliberately fail-closed until local order mirroring lands, because every
order id the platform exposes must resolve to a persisted ``Order`` row and a
portfolio — a half-mirrored order book is worse than a refused one.

Nothing here decides risk or policy: :class:`~app.auto_trading.gateway.BrokerSafetyGateway`
and the risk engine remain the only path to an order, for every provider.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.brokers.alpaca.client import AlpacaClient
from app.brokers.alpaca.mapping import map_account, map_clock, map_position, map_quote
from app.brokers.base import BrokerAdapter
from app.brokers.exceptions import BrokerConfigurationError, BrokerUnavailableError
from app.brokers.types import (
    BrokerAccountState,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerPosition,
    BrokerQuote,
    Fill,
    MarketClock,
)
from app.core.config import Settings, get_settings
from app.models.broker import BrokerAccount
from app.models.enums import BrokerEnvironment

PROVIDER = "alpaca"

_ORDERS_DISABLED_MESSAGE = (
    "Alpaca order routing is not enabled yet: external orders need a persisted local "
    "order mirror (portfolio + idempotency) which is not implemented in this build. "
    "Read operations and connection testing are supported."
)


class AlpacaBrokerAdapter(BrokerAdapter):
    """Read-side Alpaca adapter bound to a single broker account."""

    name = PROVIDER

    def __init__(
        self,
        account: BrokerAccount,
        client: AlpacaClient,
        *,
        settings: Settings | None = None,
        quote_stale_after_seconds: float = 60.0,
    ) -> None:
        self._settings = settings or get_settings()
        self._account = account
        self._client = client
        self._quote_stale_after_seconds = quote_stale_after_seconds
        if account.environment is BrokerEnvironment.LIVE:
            allowed, missing = self._settings.live_trading_allowed()
            if not self._settings.LIVE_TRADING_ALLOWED or not allowed:
                raise BrokerConfigurationError(
                    "live Alpaca routing is locked",
                    details={"missing_requirements": missing or ["LIVE_TRADING_ALLOWED"]},
                )

    @property
    def environment(self) -> BrokerEnvironment:
        return self._account.environment

    async def aclose(self) -> None:
        await self._client.aclose()

    # --- account ------------------------------------------------------------
    async def _account_state(self) -> BrokerAccountState:
        payload = await self._client.get_account()
        if not isinstance(payload, dict):
            raise BrokerUnavailableError("Alpaca returned no account payload")
        return map_account(
            payload,
            broker_account_id=self._account.id,
            environment=self._account.environment,
        )

    async def get_account(self) -> BrokerAccountState:
        return await self._account_state()

    async def get_balance(self) -> Decimal:
        return (await self._account_state()).cash

    async def get_buying_power(self) -> Decimal:
        return (await self._account_state()).buying_power

    # --- positions ----------------------------------------------------------
    async def get_positions(self) -> list[BrokerPosition]:
        return [map_position(row) for row in await self._client.get_positions()]

    async def get_position(self, symbol: str) -> BrokerPosition | None:
        payload = await self._client.get_position(symbol.upper())
        return map_position(payload) if payload else None

    # --- market data --------------------------------------------------------
    async def get_quote(self, symbol: str) -> BrokerQuote:
        snapshot = await self._client.get_snapshot(symbol)
        if not snapshot:
            raise BrokerUnavailableError(
                f"Alpaca has no quote for {symbol}",
                details={"provider": PROVIDER, "symbol": symbol},
            )
        return map_quote(
            snapshot,
            symbol=symbol,
            received_at=datetime.now(UTC),
            stale_after_seconds=self._quote_stale_after_seconds,
        )

    async def get_market_clock(self) -> MarketClock:
        return map_clock(await self._client.get_clock())

    # --- orders (fail closed until local mirroring lands) -------------------
    async def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        _ = request
        raise BrokerConfigurationError(
            _ORDERS_DISABLED_MESSAGE, details={"provider": PROVIDER, "operation": "submit_order"}
        )

    async def cancel_order(self, order_id: uuid.UUID | str) -> BrokerOrderResult:
        _ = order_id
        raise BrokerConfigurationError(
            _ORDERS_DISABLED_MESSAGE, details={"provider": PROVIDER, "operation": "cancel_order"}
        )

    async def get_order(self, order_id: uuid.UUID | str) -> BrokerOrderResult:
        _ = order_id
        raise BrokerConfigurationError(
            _ORDERS_DISABLED_MESSAGE, details={"provider": PROVIDER, "operation": "get_order"}
        )

    async def get_orders(
        self, *, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[BrokerOrderResult]:
        _ = (status, limit, offset)
        raise BrokerConfigurationError(
            _ORDERS_DISABLED_MESSAGE, details={"provider": PROVIDER, "operation": "get_orders"}
        )

    async def process_open_orders(self) -> list[Fill]:
        return []
