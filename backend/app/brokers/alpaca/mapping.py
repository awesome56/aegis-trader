"""Pure mappings between Alpaca payloads and provider-neutral broker DTOs.

No I/O happens here, which makes every translation unit-testable from a
fixture. Alpaca serialises numbers as strings, so money always passes through
``Decimal(str(...))``; nothing is parsed with ``float``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.brokers.exceptions import (
    BrokerUnavailableError,
    UnsupportedOrderTypeError,
    UnsupportedTimeInForceError,
)
from app.brokers.types import (
    BrokerAccountState,
    BrokerOrderResult,
    BrokerPosition,
    BrokerQuote,
    BrokerStatus,
    MarketClock,
)
from app.models.enums import (
    BrokerEnvironment,
    OrderStatus,
    OrderType,
    PositionSide,
    TimeInForce,
    TradeSide,
)

PROVIDER = "alpaca"
ZERO = Decimal("0")
HUNDRED = Decimal("100")


def to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def to_decimal_or_zero(value: Any) -> Decimal:
    parsed = to_decimal(value)
    return parsed if parsed is not None else ZERO


def to_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


# --- status / enum translation ---------------------------------------------
ALPACA_STATUS_MAP: dict[str, OrderStatus] = {
    "new": OrderStatus.ACCEPTED,
    "accepted": OrderStatus.ACCEPTED,
    "pending_new": OrderStatus.SUBMITTED,
    "accepted_for_bidding": OrderStatus.ACCEPTED,
    "pending_cancel": OrderStatus.CANCELLED,
    "canceled": OrderStatus.CANCELLED,
    "pending_replace": OrderStatus.ACCEPTED,
    "replaced": OrderStatus.ACCEPTED,
    "partially_filled": OrderStatus.PARTIALLY_FILLED,
    "filled": OrderStatus.FILLED,
    "rejected": OrderStatus.REJECTED,
    "expired": OrderStatus.CANCELLED,
    "done_for_day": OrderStatus.ACCEPTED,
    "stopped": OrderStatus.ACCEPTED,
    "suspended": OrderStatus.ACCEPTED,
    "held": OrderStatus.ACCEPTED,
}

ALPACA_ORDER_TYPE_MAP: dict[str, OrderType] = {
    "market": OrderType.MARKET,
    "limit": OrderType.LIMIT,
    "stop": OrderType.STOP,
    "stop_limit": OrderType.STOP_LIMIT,
}

OUR_ORDER_TYPE_MAP: dict[OrderType, str] = {
    OrderType.MARKET: "market",
    OrderType.LIMIT: "limit",
    OrderType.STOP: "stop",
    OrderType.STOP_LIMIT: "stop_limit",
}

OUR_TIF_MAP: dict[TimeInForce, str] = {
    TimeInForce.DAY: "day",
    TimeInForce.GTC: "gtc",
}

ALPACA_TIF_MAP: dict[str, TimeInForce] = {
    "day": TimeInForce.DAY,
    "gtc": TimeInForce.GTC,
}


def map_status(value: Any) -> OrderStatus:
    return ALPACA_STATUS_MAP.get(str(value or "").lower(), OrderStatus.SUBMITTED)


def map_order_type(value: Any) -> OrderType:
    mapped = ALPACA_ORDER_TYPE_MAP.get(str(value or "").lower())
    if mapped is None:
        raise UnsupportedOrderTypeError(f"Alpaca order type {value!r} is not supported")
    return mapped


def map_time_in_force(value: Any) -> TimeInForce:
    mapped = ALPACA_TIF_MAP.get(str(value or "").lower())
    if mapped is None:
        raise UnsupportedTimeInForceError(f"Alpaca time-in-force {value!r} is not supported")
    return mapped


def map_side(value: Any) -> TradeSide:
    return TradeSide.BUY if str(value or "").lower() == "buy" else TradeSide.SELL


def to_alpaca_order_payload(
    *,
    symbol: str,
    side: TradeSide,
    order_type: OrderType,
    quantity: Decimal,
    time_in_force: TimeInForce,
    limit_price: Decimal | None,
    stop_price: Decimal | None,
    client_order_id: str,
) -> dict[str, Any]:
    """Build the ``POST /v2/orders`` body.

    The idempotency key travels as ``client_order_id`` so a retry can never
    double-submit: Alpaca rejects a duplicate ``client_order_id``.
    """
    mapped_type = OUR_ORDER_TYPE_MAP.get(order_type)
    if mapped_type is None:
        raise UnsupportedOrderTypeError(f"{order_type} is not supported by the Alpaca adapter")
    mapped_tif = OUR_TIF_MAP.get(time_in_force)
    if mapped_tif is None:
        raise UnsupportedTimeInForceError(
            f"{time_in_force} is not supported by the Alpaca adapter"
        )
    payload: dict[str, Any] = {
        "symbol": symbol.upper(),
        "side": side.value.lower(),
        "type": mapped_type,
        "time_in_force": mapped_tif,
        "qty": str(quantity),
        "client_order_id": client_order_id,
    }
    if order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
        payload["limit_price"] = str(limit_price)
    if order_type in (OrderType.STOP, OrderType.STOP_LIMIT):
        payload["stop_price"] = str(stop_price)
    return payload


# --- DTO mappers ------------------------------------------------------------
def map_account(
    payload: dict[str, Any],
    *,
    broker_account_id: uuid.UUID,
    environment: BrokerEnvironment,
) -> BrokerAccountState:
    _ = environment
    long_value = to_decimal_or_zero(payload.get("long_market_value"))
    short_value = to_decimal_or_zero(payload.get("short_market_value"))
    external = payload.get("account_number") or payload.get("id")
    return BrokerAccountState(
        broker_account_id=broker_account_id,
        external_account_id=str(external) if external else None,
        provider=PROVIDER,
        currency=str(payload.get("currency") or "USD"),
        status=BrokerStatus.CONNECTED,
        cash=to_decimal_or_zero(payload.get("cash")),
        buying_power=to_decimal_or_zero(payload.get("buying_power")),
        equity=to_decimal_or_zero(payload.get("portfolio_value") or payload.get("equity")),
        market_value=long_value - short_value,
        realized_pnl=ZERO,
        unrealized_pnl=ZERO,
    )


def map_position(payload: dict[str, Any]) -> BrokerPosition:
    quantity = to_decimal_or_zero(payload.get("qty"))
    percent = to_decimal(payload.get("unrealized_plpc"))
    return BrokerPosition(
        symbol=str(payload.get("symbol") or "").upper(),
        side=PositionSide.SHORT if quantity < 0 else PositionSide.LONG,
        quantity=abs(quantity),
        average_entry_price=to_decimal_or_zero(payload.get("avg_entry_price")),
        current_price=to_decimal(payload.get("current_price")),
        market_value=to_decimal_or_zero(payload.get("market_value")),
        cost_basis=to_decimal_or_zero(payload.get("cost_basis")),
        unrealized_pnl=to_decimal_or_zero(payload.get("unrealized_pl")),
        unrealized_pnl_percent=(percent * HUNDRED) if percent is not None else ZERO,
        realized_pnl=ZERO,
    )


def map_order(payload: dict[str, Any], *, order_id: uuid.UUID) -> BrokerOrderResult:
    return BrokerOrderResult(
        order_id=order_id,
        broker_order_id=str(payload.get("id")) if payload.get("id") else None,
        client_order_id=payload.get("client_order_id"),
        symbol=str(payload.get("symbol") or "").upper(),
        side=map_side(payload.get("side")),
        order_type=map_order_type(payload.get("type")),
        time_in_force=map_time_in_force(payload.get("time_in_force")),
        quantity=to_decimal_or_zero(payload.get("qty")),
        filled_quantity=to_decimal_or_zero(payload.get("filled_qty")),
        limit_price=to_decimal(payload.get("limit_price")),
        stop_price=to_decimal(payload.get("stop_price")),
        average_fill_price=to_decimal(payload.get("filled_avg_price")),
        status=map_status(payload.get("status")),
        created_at=to_datetime(payload.get("created_at")),
        updated_at=to_datetime(payload.get("updated_at")),
        submitted_at=to_datetime(payload.get("submitted_at")),
        filled_at=to_datetime(payload.get("filled_at")),
        cancelled_at=to_datetime(payload.get("canceled_at")),
    )


def map_clock(payload: dict[str, Any]) -> MarketClock:
    is_open = bool(payload.get("is_open"))
    return MarketClock(
        is_open=is_open,
        session="regular" if is_open else "closed",
        current_time=to_datetime(payload.get("timestamp")) or datetime.now(UTC),
        next_open=to_datetime(payload.get("next_open")),
        next_close=to_datetime(payload.get("next_close")),
        provider=PROVIDER,
    )


def map_quote(
    snapshot: dict[str, Any],
    *,
    symbol: str,
    received_at: datetime | None = None,
    stale_after_seconds: float = 60.0,
) -> BrokerQuote:
    """Map an Alpaca stock snapshot into a :class:`BrokerQuote`.

    ``is_stale`` is derived from the exchange timestamp, not the wall clock at
    request time, so a closed market never looks fresh.
    """
    received = received_at or datetime.now(UTC)
    quote = snapshot.get("latestQuote") or {}
    trade = snapshot.get("latestTrade") or {}
    bid = to_decimal(quote.get("bp"))
    ask = to_decimal(quote.get("ap"))
    last = to_decimal(trade.get("p"))
    if last is None:
        for key in ("minuteBar", "dailyBar", "prevDailyBar"):
            last = to_decimal((snapshot.get(key) or {}).get("c"))
            if last is not None:
                break
    if last is None and bid is not None and ask is not None:
        last = (bid + ask) / 2
    if last is None:
        raise BrokerUnavailableError(f"Alpaca returned no usable price for {symbol}")
    market_timestamp = to_datetime(quote.get("t")) or to_datetime(trade.get("t")) or received
    age = max(0.0, (received - market_timestamp).total_seconds())
    return BrokerQuote(
        symbol=symbol.upper(),
        bid=bid,
        ask=ask,
        last=last,
        mid=(bid + ask) / 2 if bid is not None and ask is not None else None,
        provider=PROVIDER,
        market_timestamp=market_timestamp,
        received_at=received,
        age_seconds=age,
        is_stale=age > stale_after_seconds,
    )
