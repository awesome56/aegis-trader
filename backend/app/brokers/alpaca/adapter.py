"""Alpaca broker adapter.

Reads proxy straight to Alpaca; writes are *mirrored*: the platform owns the
local ``Order``/``Execution``/``Position`` records (the rest of the app reads
them) while Alpaca owns the truth of what actually happened. Every submission
carries the platform idempotency key as Alpaca's ``client_order_id``, so a retry
converges on one remote order instead of double-submitting.

Risk and policy decisions never live here: for every provider the only route to
an order is
:class:`~app.auto_trading.gateway.BrokerSafetyGateway` → RiskEngine →
``OrderManager``. This adapter only translates.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.alpaca.client import AlpacaClient
from app.brokers.alpaca.mapping import (
    map_account,
    map_clock,
    map_position,
    map_quote,
    map_status,
    to_alpaca_order_payload,
    to_datetime,
    to_decimal,
    to_decimal_or_zero,
)
from app.brokers.base import BrokerAdapter
from app.brokers.exceptions import (
    BrokerConfigurationError,
    BrokerUnavailableError,
    OrderNotCancellableError,
    OrderNotFoundError,
)
from app.brokers.state import CANCELLABLE_STATES, can_transition
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
from app.core.exceptions import AegisError
from app.core.logging import get_logger
from app.models.broker import BrokerAccount
from app.models.enums import BrokerEnvironment, OrderStatus
from app.models.order import Execution, Order
from app.models.portfolio import Portfolio
from app.repositories.order import ExecutionRepository, OrderRepository
from app.repositories.position import PositionRepository

logger = get_logger(__name__)

PROVIDER = "alpaca"
ZERO = Decimal("0")

TERMINAL = (
    OrderStatus.FILLED,
    OrderStatus.CANCELLED,
    OrderStatus.REJECTED,
    OrderStatus.FAILED,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class AlpacaBrokerAdapter(BrokerAdapter):
    """Alpaca adapter bound to a single broker account and its portfolio."""

    name = PROVIDER

    def __init__(
        self,
        session: AsyncSession,
        account: BrokerAccount,
        portfolio: Portfolio,
        client: AlpacaClient,
        *,
        settings: Settings | None = None,
        quote_stale_after_seconds: float = 60.0,
    ) -> None:
        self._settings = settings or get_settings()
        self._session = session
        self._account = account
        self._portfolio = portfolio
        self._client = client
        self._quote_stale_after_seconds = quote_stale_after_seconds
        self._orders = OrderRepository(session)
        self._executions = ExecutionRepository(session)
        self._positions = PositionRepository(session)
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

    # --- positions (mirrored so the rest of the app can read them) ----------
    async def get_positions(self) -> list[BrokerPosition]:
        positions = [map_position(row) for row in await self._client.get_positions()]
        await self._mirror_positions(positions)
        return positions

    async def get_position(self, symbol: str) -> BrokerPosition | None:
        payload = await self._client.get_position(symbol.upper())
        position = map_position(payload) if payload else None
        closed = {symbol.upper()} if position is None else set()
        await self._mirror_positions([position] if position else [], closed_symbols=closed)
        return position

    async def _mirror_positions(
        self, remote: list[BrokerPosition], *, closed_symbols: set[str] | None = None
    ) -> None:
        local = {row.symbol: row for row in await self._positions.list_open(self._portfolio.id)}
        seen: set[str] = set()
        now = _now()
        for item in remote:
            seen.add(item.symbol)
            row = local.get(item.symbol)
            if row is None:
                row = PositionMirror(
                    portfolio_id=self._portfolio.id,
                    symbol=item.symbol,
                    side=item.side,
                    quantity=item.quantity,
                    average_entry_price=item.average_entry_price,
                    opened_at=now,
                )
                self._session.add(row)
            row.side = item.side
            row.quantity = item.quantity
            row.average_entry_price = item.average_entry_price
            row.current_price = item.current_price
            row.cost_basis = item.cost_basis
            row.market_value = item.market_value
            row.unrealized_pnl = item.unrealized_pnl
            row.realized_pnl = item.realized_pnl
            row.is_open = True
            row.last_marked_at = now
            row.updated_at = now
        for symbol, row in local.items():
            if symbol in seen:
                continue
            if closed_symbols is not None and symbol not in closed_symbols:
                continue
            row.is_open = False
            row.quantity = ZERO
            row.market_value = ZERO
            row.closed_at = now
            row.updated_at = now
        await self._session.flush()

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
            received_at=_now(),
            stale_after_seconds=self._quote_stale_after_seconds,
        )

    async def get_market_clock(self) -> MarketClock:
        return map_clock(await self._client.get_clock())

    # --- orders -------------------------------------------------------------
    def _to_result(self, order: Order) -> BrokerOrderResult:
        return BrokerOrderResult(
            order_id=order.id,
            broker_order_id=order.broker_order_id,
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            time_in_force=order.time_in_force,
            quantity=order.quantity,
            filled_quantity=order.filled_quantity,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            average_fill_price=order.average_fill_price,
            commission=order.fees,
            status=order.status,
            error_message=order.error_message,
            created_at=order.created_at,
            updated_at=order.updated_at,
            submitted_at=order.submitted_at,
            filled_at=order.filled_at,
            cancelled_at=order.cancelled_at,
        )

    async def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        key = request.resolved_idempotency_key

        # Idempotent replay: an order already exists for this key, so converge on
        # it rather than sending a second one to the venue.
        existing = await self._orders.get_by_idempotency_key(key, self._account.id)
        if existing is not None:
            return await self._refresh(existing)

        now = _now()
        order = Order(
            portfolio_id=request.portfolio_id or self._portfolio.id,
            broker_account_id=self._account.id,
            asset_id=request.asset_id,
            symbol=request.symbol.upper(),
            side=request.side,
            order_type=request.order_type,
            time_in_force=request.time_in_force,
            status=OrderStatus.SUBMITTED,
            quantity=request.quantity,
            filled_quantity=ZERO,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            idempotency_key=key,
            client_order_id=request.client_order_id or key,
            submitted_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(order)
        try:
            await self._session.flush()
        except IntegrityError:
            # Concurrent duplicate submission: fall back to the winning row.
            await self._session.rollback()
            winner = await self._orders.get_by_idempotency_key(key, self._account.id)
            if winner is None:  # pragma: no cover - defensive
                raise
            return await self._refresh(winner)

        payload = to_alpaca_order_payload(
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            time_in_force=order.time_in_force,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            client_order_id=order.client_order_id or key,
        )
        order.raw_request = payload
        try:
            remote = await self._client.submit_order(payload)
        except AegisError as exc:
            order.status = OrderStatus.REJECTED
            order.error_message = exc.message[:2000]
            order.updated_at = _now()
            await self._session.flush()
            raise
        await self._apply_remote(order, remote)
        return self._to_result(order)

    async def cancel_order(self, order_id: uuid.UUID | str) -> BrokerOrderResult:
        order = await self._load_order(order_id)
        if order is None:
            raise OrderNotFoundError(f"Order {order_id} not found for this account")
        if order.status in TERMINAL or order.status not in CANCELLABLE_STATES:
            raise OrderNotCancellableError(
                f"Order {order.id} is {order.status.value} and cannot be cancelled"
            )
        now = _now()
        if order.broker_order_id is None:
            # Never reached the venue (e.g. the submit call failed): cancel locally.
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = now
            order.updated_at = now
            await self._session.flush()
            return self._to_result(order)

        try:
            await self._client.cancel_order(order.broker_order_id)
        except AegisError as exc:
            logger.warning(
                "alpaca_cancel_failed", order_id=str(order.id), error=exc.message
            )
            raise
        remote = await self._client.get_order(order.broker_order_id)
        await self._apply_remote(order, remote, fallback_status=OrderStatus.CANCELLED)
        return self._to_result(order)

    async def get_order(self, order_id: uuid.UUID | str) -> BrokerOrderResult:
        order = await self._load_order(order_id)
        if order is None:
            raise OrderNotFoundError(f"Order {order_id} not found for this account")
        return await self._refresh(order)

    async def get_orders(
        self, *, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[BrokerOrderResult]:
        parsed: OrderStatus | None = None
        if status:
            try:
                parsed = OrderStatus(status)
            except ValueError:
                parsed = None
        rows = await self._orders.list_for_account(
            self._account.id, status=parsed, limit=limit, offset=offset
        )
        return [self._to_result(row) for row in rows]

    async def process_open_orders(self) -> list[Fill]:
        fills: list[Fill] = []
        for order in await self._orders.list_open_for_account(self._account.id):
            if order.broker_order_id is None:
                continue
            remote = await self._client.get_order(order.broker_order_id)
            fill = await self._apply_remote(order, remote)
            if fill is not None:
                fills.append(fill)
        return fills

    # --- order helpers ------------------------------------------------------
    async def _load_order(self, order_id: uuid.UUID | str) -> Order | None:
        try:
            parsed = order_id if isinstance(order_id, uuid.UUID) else uuid.UUID(str(order_id))
        except (ValueError, AttributeError):
            return None
        return await self._orders.get_scoped(parsed, self._account.id)

    async def _refresh(self, order: Order) -> BrokerOrderResult:
        if order.broker_order_id is not None:
            remote = await self._client.get_order(order.broker_order_id)
            if remote is not None:
                await self._apply_remote(order, remote)
        return self._to_result(order)

    async def _apply_remote(
        self,
        order: Order,
        remote: dict | None,
        *,
        fallback_status: OrderStatus | None = None,
    ) -> Fill | None:
        """Reconcile a remote order payload onto the local mirror.

        Records an ``Execution`` for any newly filled quantity and returns the
        resulting :class:`Fill` (or ``None`` when nothing new filled).
        """
        now = _now()
        if remote is None:
            if fallback_status is not None and can_transition(order.status, fallback_status):
                order.status = fallback_status
                if fallback_status is OrderStatus.CANCELLED:
                    order.cancelled_at = order.cancelled_at or now
            order.updated_at = now
            await self._session.flush()
            return None

        order.broker_order_id = str(remote.get("id") or order.broker_order_id or "") or None
        order.raw_response = remote

        fill: Fill | None = None
        filled = to_decimal_or_zero(remote.get("filled_qty"))
        price = to_decimal(remote.get("filled_avg_price"))
        if filled > order.filled_quantity:
            delta = filled - order.filled_quantity
            execution_price = price or order.average_fill_price or order.limit_price or ZERO
            executed_at = (
                to_datetime(remote.get("filled_at"))
                or to_datetime(remote.get("updated_at"))
                or now
            )
            execution = Execution(
                order_id=order.id,
                quantity=delta,
                price=execution_price,
                gross_amount=delta * execution_price,
                net_amount=delta * execution_price,
                fees=ZERO,
                commission=ZERO,
                slippage=ZERO,
                broker_execution_id=str(remote.get("id") or "") or None,
                executed_at=executed_at,
                raw=remote,
            )
            await self._executions.add(execution)
            quantity = order.filled_quantity + delta
            # Weighted average across the previous fills and this delta.
            if order.average_fill_price and order.filled_quantity > 0:
                total = (
                    order.average_fill_price * order.filled_quantity
                    + execution_price * delta
                )
                order.average_fill_price = total / quantity
            else:
                order.average_fill_price = execution_price
            order.filled_quantity = quantity
            fill = Fill(
                execution_id=execution.id,
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=delta,
                price=execution_price,
                gross_amount=delta * execution_price,
                commission=ZERO,
                net_amount=delta * execution_price,
                executed_at=executed_at,
            )

        target = map_status(remote.get("status"))
        if can_transition(order.status, target):
            order.status = target
        elif order.status in TERMINAL:
            logger.info(
                "alpaca_terminal_status_kept",
                order_id=str(order.id),
                local=order.status.value,
                remote=target.value,
            )
        elif order.status is not target:
            order.status = target

        if order.status is OrderStatus.FILLED and order.filled_at is None:
            order.filled_at = to_datetime(remote.get("filled_at")) or now
        if order.status is OrderStatus.CANCELLED and order.cancelled_at is None:
            order.cancelled_at = to_datetime(remote.get("canceled_at")) or now
        order.updated_at = now
        await self._session.flush()
        return fill


# Imported late to keep the module's public surface tidy while still giving the
# mirror helper a typed constructor.
from app.models.position import Position as PositionMirror  # noqa: E402
