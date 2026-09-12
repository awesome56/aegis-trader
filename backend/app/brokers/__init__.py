"""Broker abstraction and the simulated paper broker (Phase 3).

Boundary rules: this package must not import ``app.risk``, ``app.agents``,
``app.strategies`` or the future order-execution pipeline, and ``app.market``
must not import this package.
"""

from app.brokers.accounting import (
    add_to_position,
    apply_slippage,
    commission_for,
    market_value,
    reduce_position,
    return_percent,
    unrealized_pnl,
)
from app.brokers.base import BrokerAdapter
from app.brokers.bootstrap import ensure_paper_account
from app.brokers.exceptions import (
    BrokerConfigurationError,
    BrokerError,
    BrokerRejectedOrderError,
    InsufficientFundsError,
    InsufficientPositionError,
    InvalidOrderError,
    OrderNotCancellableError,
    OrderNotFoundError,
    UnsupportedOrderTypeError,
)
from app.brokers.factory import resolve_broker_provider
from app.brokers.paper import PaperBrokerAdapter
from app.brokers.types import (
    BrokerAccountState,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerPosition,
    BrokerQuote,
    BrokerStatus,
    Fill,
    MarketClock,
)

__all__ = [
    "BrokerAccountState",
    "BrokerAdapter",
    "BrokerConfigurationError",
    "BrokerError",
    "BrokerOrderRequest",
    "BrokerOrderResult",
    "BrokerPosition",
    "BrokerQuote",
    "BrokerRejectedOrderError",
    "BrokerStatus",
    "Fill",
    "InsufficientFundsError",
    "InsufficientPositionError",
    "InvalidOrderError",
    "MarketClock",
    "OrderNotCancellableError",
    "OrderNotFoundError",
    "PaperBrokerAdapter",
    "UnsupportedOrderTypeError",
    "add_to_position",
    "apply_slippage",
    "commission_for",
    "ensure_paper_account",
    "market_value",
    "reduce_position",
    "resolve_broker_provider",
    "return_percent",
    "unrealized_pnl",
]
