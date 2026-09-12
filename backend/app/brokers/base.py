"""Abstract broker adapter interface.

Trading logic depends only on this interface. Provider SDKs and transport
details stay inside concrete adapters; provider errors are normalised in
``app.brokers.exceptions`` before they reach callers.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from decimal import Decimal

from app.brokers.types import (
    BrokerAccountState,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerPosition,
    BrokerQuote,
    Fill,
    MarketClock,
)


class BrokerAdapter(ABC):
    """Provider-neutral brokerage contract.

    An instance is bound to a single broker account; multi-account support is
    achieved by constructing one adapter per account.
    """

    name: str = "base"

    @abstractmethod
    async def get_account(self) -> BrokerAccountState:
        """Return the current account state."""

    @abstractmethod
    async def get_balance(self) -> Decimal:
        """Return settled cash."""

    @abstractmethod
    async def get_buying_power(self) -> Decimal:
        """Return buying power (cash minus reserved pending BUY notional)."""

    @abstractmethod
    async def get_positions(self) -> list[BrokerPosition]:
        """Return all open positions."""

    @abstractmethod
    async def get_position(self, symbol: str) -> BrokerPosition | None:
        """Return the open position for ``symbol`` or ``None``."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> BrokerQuote:
        """Return a display quote for ``symbol`` (may be stale; see ``is_stale``)."""

    @abstractmethod
    async def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        """Submit an order idempotently and return its current state."""

    @abstractmethod
    async def cancel_order(self, order_id: uuid.UUID | str) -> BrokerOrderResult:
        """Cancel a working order."""

    @abstractmethod
    async def get_order(self, order_id: uuid.UUID | str) -> BrokerOrderResult:
        """Return a single order scoped to this account."""

    @abstractmethod
    async def get_orders(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BrokerOrderResult]:
        """Return orders scoped to this account, newest first."""

    @abstractmethod
    async def get_market_clock(self) -> MarketClock:
        """Return the market session clock."""

    @abstractmethod
    async def process_open_orders(self) -> list[Fill]:
        """Re-evaluate open orders against fresh quotes and return new fills."""
