"""Broker REST API.

Read endpoints expose account state, positions, orders and the market clock.
``POST``/``DELETE`` order endpoints are **paper-mode manual testing interfaces**
only and are deliberately separate from the future automated
TradeProposal → Risk → OrderManager pipeline (Phase 7). They require the
authenticated owner, run only when ``BROKER_PROVIDER=paper``, and are idempotent.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.auth.dependencies import CurrentUser, DbSession
from app.brokers.dependencies import BrokerDep
from app.brokers.types import BrokerOrderRequest
from app.core.config import get_settings
from app.market.exceptions import StaleMarketDataError
from app.models.enums import NotificationSeverity
from app.notifications.service import CATEGORY_BROKER, CATEGORY_TRADING, NotificationService
from app.schemas.broker import (
    BrokerAccountSchema,
    BrokerOrderListSchema,
    BrokerOrderSchema,
    BrokerPositionSchema,
    BrokerQuoteSchema,
    MarketClockSchema,
    OrderCreateRequest,
)

router = APIRouter(prefix="/broker", tags=["broker"])

PAPER_ONLY_DETAIL = "Manual order endpoints are available in paper mode only."


def _ensure_paper_mode() -> None:
    from app.brokers.exceptions import BrokerConfigurationError

    if get_settings().BROKER_PROVIDER.strip().lower() != "paper":
        raise BrokerConfigurationError(PAPER_ONLY_DETAIL)


async def _notify_order(session, user_id, result) -> None:  # noqa: ANN001
    service = NotificationService(session)
    label = f"{result.side.value} {result.quantity.normalize()} {result.symbol}"
    if result.status.value == "FILLED":
        await service.create_notification(
            user_id=user_id,
            category=CATEGORY_TRADING,
            title="Order filled",
            message=f"{label} filled at {result.average_fill_price}",
            severity=NotificationSeverity.INFO,
            payload={"order_id": str(result.order_id)},
        )
    elif result.status.value == "PARTIALLY_FILLED":
        await service.create_notification(
            user_id=user_id,
            category=CATEGORY_TRADING,
            title="Order partially filled",
            message=f"{label} partially filled ({result.filled_quantity} of {result.quantity})",
            severity=NotificationSeverity.INFO,
            payload={"order_id": str(result.order_id)},
        )
    elif result.status.value == "REJECTED":
        await service.create_notification(
            user_id=user_id,
            category=CATEGORY_BROKER,
            title="Order rejected",
            message=f"{label} rejected: {result.error_message or 'unknown reason'}",
            severity=NotificationSeverity.WARNING,
            payload={"order_id": str(result.order_id)},
        )
    elif result.status.value == "CANCELLED":
        await service.create_notification(
            user_id=user_id,
            category=CATEGORY_TRADING,
            title="Order cancelled",
            message=f"{label} cancelled",
            severity=NotificationSeverity.INFO,
            payload={"order_id": str(result.order_id)},
        )


@router.get("/account", response_model=BrokerAccountSchema, summary="Paper broker account state")
async def get_account(broker: BrokerDep) -> BrokerAccountSchema:
    return BrokerAccountSchema.model_validate(await broker.get_account())


@router.get("/positions", response_model=list[BrokerPositionSchema], summary="Broker positions")
async def get_positions(broker: BrokerDep) -> list[BrokerPositionSchema]:
    return [BrokerPositionSchema.model_validate(p) for p in await broker.get_positions()]


@router.get(
    "/positions/{symbol}",
    response_model=BrokerPositionSchema,
    summary="Broker position by symbol",
)
async def get_position(symbol: str, broker: BrokerDep) -> BrokerPositionSchema:
    from app.brokers.exceptions import OrderNotFoundError

    position = await broker.get_position(symbol)
    if position is None:
        raise OrderNotFoundError(f"No open position for {symbol.upper()}")
    return BrokerPositionSchema.model_validate(position)


@router.get("/quote/{symbol}", response_model=BrokerQuoteSchema, summary="Quote via the broker")
async def get_quote(symbol: str, broker: BrokerDep) -> BrokerQuoteSchema:
    return BrokerQuoteSchema.model_validate(await broker.get_quote(symbol))


@router.get("/clock", response_model=MarketClockSchema, summary="Market clock")
async def get_clock(broker: BrokerDep) -> MarketClockSchema:
    return MarketClockSchema.model_validate(await broker.get_market_clock())


@router.get("/orders", response_model=BrokerOrderListSchema, summary="List broker orders")
async def list_orders(
    broker: BrokerDep,
    status: str | None = Query(default=None, description="Filter by order status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> BrokerOrderListSchema:
    orders = await broker.get_orders(status=status, limit=limit, offset=offset)
    return BrokerOrderListSchema(
        items=[BrokerOrderSchema.from_result(order) for order in orders],
        total=len(orders),
    )


@router.get("/orders/{order_id}", response_model=BrokerOrderSchema, summary="Broker order by id")
async def get_order(order_id: uuid.UUID, broker: BrokerDep) -> BrokerOrderSchema:
    return BrokerOrderSchema.from_result(await broker.get_order(order_id))


@router.post(
    "/orders",
    response_model=BrokerOrderSchema,
    status_code=201,
    summary="Submit a manual paper order",
)
async def submit_order(
    payload: OrderCreateRequest,
    broker: BrokerDep,
    session: DbSession,
    user: CurrentUser,
) -> BrokerOrderSchema:
    _ensure_paper_mode()
    request = BrokerOrderRequest(
        symbol=payload.symbol,
        side=payload.side,
        order_type=payload.order_type,
        quantity=payload.quantity,
        limit_price=payload.limit_price,
        stop_price=payload.stop_price,
        time_in_force=payload.time_in_force,
        client_order_id=payload.client_order_id,
        idempotency_key=payload.idempotency_key,
    )
    try:
        result = await broker.submit_order(request)
    except StaleMarketDataError:
        await NotificationService(session).create_notification(
            user_id=user.id,
            category=CATEGORY_BROKER,
            title="Stale market data prevented execution",
            message=f"{payload.symbol.upper()} order was not executed because the price was stale.",
            severity=NotificationSeverity.WARNING,
            payload={"symbol": payload.symbol.upper()},
        )
        raise
    await _notify_order(session, user.id, result)
    return BrokerOrderSchema.from_result(result)


@router.delete(
    "/orders/{order_id}",
    response_model=BrokerOrderSchema,
    summary="Cancel a manual paper order",
)
async def cancel_order(
    order_id: uuid.UUID,
    broker: BrokerDep,
    session: DbSession,
    user: CurrentUser,
) -> BrokerOrderSchema:
    _ensure_paper_mode()
    result = await broker.cancel_order(order_id)
    await _notify_order(session, user.id, result)
    return BrokerOrderSchema.from_result(result)


@router.post(
    "/orders/process",
    response_model=list[BrokerOrderSchema],
    summary="Re-evaluate open paper orders (testing/worker hook)",
)
async def process_open_orders(broker: BrokerDep, session: DbSession) -> list[BrokerOrderSchema]:
    _ensure_paper_mode()
    fills = await broker.process_open_orders()
    processed = {fill.order_id for fill in fills}
    results = []
    for order_id in processed:
        results.append(BrokerOrderSchema.from_result(await broker.get_order(order_id)))
    return results
