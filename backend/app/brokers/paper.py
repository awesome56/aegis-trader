"""Deterministic simulated broker.

The paper broker is a realistic broker-side simulator: it owns broker cash,
buying power, orders, fills and positions, and its state is derived entirely from
persistence so a restart never resets the account. It prices every execution from
Phase 2's :class:`~app.market.services.market_data.MarketDataService` and fails
closed on stale quotes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import ROUND_FLOOR, Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.accounting import (
    add_to_position,
    apply_slippage,
    commission_for,
    market_value,
    q,
    reduce_position,
    return_percent,
    unrealized_pnl,
)
from app.brokers.base import BrokerAdapter
from app.brokers.exceptions import (
    InvalidOrderError,
    OrderNotCancellableError,
    OrderNotFoundError,
    UnsupportedOrderTypeError,
)
from app.brokers.state import CANCELLABLE_STATES, assert_transition, is_terminal
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
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.market.domain.models import MarketQuote
from app.market.services.market_data import MarketDataService
from app.models.broker import BrokerAccount
from app.models.enums import OrderStatus, OrderType, PositionSide, TradeSide
from app.models.order import Execution, Order
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.realtime.events import DomainEvent, queue_event
from app.repositories.broker_account import BrokerAccountRepository
from app.repositories.order import ExecutionRepository, OrderRepository
from app.repositories.position import PositionRepository

logger = get_logger(__name__)

_SUPPORTED_ORDER_TYPES = {
    OrderType.MARKET,
    OrderType.LIMIT,
    OrderType.STOP,
    OrderType.STOP_LIMIT,
}


class PaperBrokerAdapter(BrokerAdapter):
    name = "paper"

    def __init__(
        self,
        session: AsyncSession,
        account: BrokerAccount,
        portfolio: Portfolio,
        market: MarketDataService,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._account = account
        self._portfolio = portfolio
        self._market = market
        self._settings = settings or get_settings()
        self._orders = OrderRepository(session)
        self._executions = ExecutionRepository(session)
        self._positions = PositionRepository(session)
        self._accounts = BrokerAccountRepository(session)
        self._user_id = account.user_id

    # --- helpers ------------------------------------------------------------
    def _emit(self, event: str, data: dict) -> None:
        queue_event(
            self._session.info,
            DomainEvent(event=event, data=data, user_id=self._user_id),
        )

    def _flat_commission(self) -> Decimal:
        return Decimal(str(self._settings.BROKER_PAPER_COMMISSION))

    async def _mark_price(self, symbol: str) -> Decimal | None:
        try:
            quote = await self._market.get_quote(symbol)
        except Exception as exc:  # noqa: BLE001 - marking must not fail reads
            logger.warning("paper_mark_unavailable", symbol=symbol, error=str(exc))
            return None
        return quote.bid if quote.bid is not None else quote.last

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

    async def _reserved_cash(self) -> Decimal:
        return await self._orders.reserved_buy_notional(self._account.id)

    async def _refresh_buying_power(self) -> None:
        reserved = await self._reserved_cash()
        self._account.buying_power = q(Decimal(str(self._account.cash_balance)) - reserved)
        self._account.updated_at = datetime.now(UTC)
        await self._session.flush()

    def _to_broker_quote(self, quote: MarketQuote) -> BrokerQuote:
        assessment = self._market.freshness.assess_quote(quote)
        return BrokerQuote(
            symbol=quote.symbol,
            bid=quote.bid,
            ask=quote.ask,
            last=quote.last,
            mid=(quote.bid + quote.ask) / 2 if quote.bid and quote.ask else quote.last,
            provider=quote.provider,
            market_timestamp=quote.market_timestamp,
            received_at=quote.received_at,
            age_seconds=round(assessment.age_seconds, 3),
            is_stale=assessment.is_stale,
        )

    # --- account ------------------------------------------------------------
    async def get_account(self) -> BrokerAccountState:
        positions = await self._positions.list_open(self._portfolio.id)
        total_market_value = Decimal("0")
        total_unrealized = Decimal("0")
        for position in positions:
            mark = await self._mark_price(position.symbol) or position.average_entry_price
            total_market_value += market_value(position.quantity, mark)
            total_unrealized += unrealized_pnl(
                position.quantity, position.average_entry_price, mark
            )

        cash = Decimal(str(self._account.cash_balance))
        return BrokerAccountState(
            broker_account_id=self._account.id,
            external_account_id=self._account.external_account_id,
            provider=self._account.broker,
            currency=self._account.currency,
            status=BrokerStatus.PAPER,
            cash=cash,
            buying_power=Decimal(str(self._account.buying_power)),
            equity=q(cash + total_market_value),
            market_value=q(total_market_value),
            realized_pnl=Decimal(str(self._account.realized_pnl)),
            unrealized_pnl=q(total_unrealized),
            created_at=self._account.created_at,
            updated_at=self._account.updated_at,
        )

    async def get_balance(self) -> Decimal:
        return Decimal(str(self._account.cash_balance))

    async def get_buying_power(self) -> Decimal:
        reserved = await self._reserved_cash()
        return q(Decimal(str(self._account.cash_balance)) - reserved)

    # --- positions ----------------------------------------------------------
    def _to_broker_position(self, position: Position, mark: Decimal) -> BrokerPosition:
        realized = Decimal(str(position.realized_pnl))
        cost = Decimal(str(position.cost_basis))
        unrealized = unrealized_pnl(position.quantity, position.average_entry_price, mark)
        return BrokerPosition(
            symbol=position.symbol,
            asset_id=position.asset_id,
            side=position.side,
            quantity=position.quantity,
            average_entry_price=position.average_entry_price,
            current_price=mark,
            market_value=market_value(position.quantity, mark),
            cost_basis=cost,
            unrealized_pnl=unrealized,
            unrealized_pnl_percent=return_percent(unrealized, cost),
            realized_pnl=realized,
            updated_at=position.updated_at,
        )

    async def get_positions(self) -> list[BrokerPosition]:
        positions = await self._positions.list_open(self._portfolio.id)
        result: list[BrokerPosition] = []
        for position in positions:
            mark = await self._mark_price(position.symbol) or position.average_entry_price
            result.append(self._to_broker_position(position, mark))
        return result

    async def get_position(self, symbol: str) -> BrokerPosition | None:
        position = await self._positions.get_open(self._portfolio.id, symbol)
        if position is None:
            return None
        mark = await self._mark_price(position.symbol) or position.average_entry_price
        return self._to_broker_position(position, mark)

    async def get_quote(self, symbol: str) -> BrokerQuote:
        return self._to_broker_quote(await self._market.get_quote(symbol))

    # --- orders -------------------------------------------------------------
    async def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        if request.order_type not in _SUPPORTED_ORDER_TYPES:
            raise UnsupportedOrderTypeError(f"Unsupported order type {request.order_type!r}")

        symbol = request.symbol.strip().upper()
        key = request.resolved_idempotency_key

        existing = await self._orders.get_by_idempotency_key(key, self._account.id)
        if existing is not None:
            return self._to_result(existing)

        # Fail closed: never create an order we cannot price from fresh data.
        fresh_quote = await self._market.get_fresh_quote(symbol)
        asset = await self._market.resolve_asset(symbol)

        now = datetime.now(UTC)
        order = Order(
            proposal_id=None,
            portfolio_id=request.portfolio_id or self._portfolio.id,
            broker_account_id=self._account.id,
            asset_id=asset.id if asset is not None else request.asset_id,
            symbol=symbol,
            side=request.side,
            order_type=request.order_type,
            time_in_force=request.time_in_force,
            status=OrderStatus.CREATED,
            quantity=request.quantity,
            filled_quantity=Decimal("0"),
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            fees=Decimal("0"),
            idempotency_key=key,
            client_order_id=request.client_order_id,
            submitted_at=now,
            created_at=now,
            updated_at=now,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(order)
                await self._session.flush()
        except IntegrityError:
            existing = await self._orders.get_by_idempotency_key(key, self._account.id)
            if existing is not None:
                return self._to_result(existing)
            raise

        self._emit(
            "order.created",
            {
                "order_id": str(order.id),
                "symbol": symbol,
                "side": request.side.value,
                "order_type": request.order_type.value,
                "quantity": str(request.quantity),
                "status": OrderStatus.CREATED.value,
            },
        )

        assert_transition(order.status, OrderStatus.SUBMITTED)
        order.status = OrderStatus.SUBMITTED
        order.accepted_at = now
        order.updated_at = now
        await self._session.flush()
        self._emit(
            "order.submitted",
            {
                "order_id": str(order.id),
                "symbol": symbol,
                "side": request.side.value,
                "status": OrderStatus.SUBMITTED.value,
            },
        )

        await self._attempt_fill(
            order, fresh_quote, allow_partial=self._settings.BROKER_PAPER_PARTIAL_FILLS
        )
        await self._refresh_buying_power()
        return self._to_result(order)

    async def cancel_order(self, order_id: uuid.UUID | str) -> BrokerOrderResult:
        order = await self._get_scoped_order(order_id)
        if order.status is OrderStatus.CANCELLED:
            raise OrderNotCancellableError("Order is already cancelled")
        if is_terminal(order.status) or order.status not in CANCELLABLE_STATES:
            raise OrderNotCancellableError(
                f"Order in status {order.status.value} cannot be cancelled"
            )
        assert_transition(order.status, OrderStatus.CANCELLED)
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now(UTC)
        order.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._refresh_buying_power()
        self._emit(
            "order.cancelled",
            {
                "order_id": str(order.id),
                "symbol": order.symbol,
                "status": OrderStatus.CANCELLED.value,
            },
        )
        return self._to_result(order)

    async def get_order(self, order_id: uuid.UUID | str) -> BrokerOrderResult:
        return self._to_result(await self._get_scoped_order(order_id))

    async def get_orders(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BrokerOrderResult]:
        parsed: OrderStatus | None = None
        if status:
            try:
                parsed = OrderStatus(status.upper())
            except ValueError as exc:
                raise InvalidOrderError(f"Unknown order status {status!r}") from exc
        orders = await self._orders.list_for_account(
            self._account.id, status=parsed, limit=limit, offset=offset
        )
        return [self._to_result(order) for order in orders]

    async def get_market_clock(self) -> MarketClock:
        status = await self._market.get_market_status()
        return MarketClock(
            is_open=status.is_open,
            session=status.session.value,
            current_time=status.timestamp,
            next_open=status.opens_at,
            next_close=status.closes_at,
            provider=status.provider,
        )

    async def process_open_orders(self) -> list[Fill]:
        orders = await self._orders.list_open_for_account(self._account.id)
        if not orders:
            return []
        quotes: dict[str, MarketQuote] = {}
        fills: list[Fill] = []
        for order in orders:
            symbol = order.symbol
            if symbol not in quotes:
                try:
                    quotes[symbol] = await self._market.get_fresh_quote(symbol)
                except Exception as exc:  # noqa: BLE001 - skip unpricable orders
                    logger.warning("paper_open_order_skip", order_id=str(order.id), error=str(exc))
                    continue
            fills.extend(await self._attempt_fill(order, quotes[symbol], allow_partial=False))
        if fills:
            await self._refresh_buying_power()
        return fills

    # --- execution internals ------------------------------------------------
    async def _get_scoped_order(self, order_id: uuid.UUID | str) -> Order:
        try:
            parsed = order_id if isinstance(order_id, uuid.UUID) else uuid.UUID(str(order_id))
        except (ValueError, TypeError) as exc:
            raise OrderNotFoundError("Invalid order id") from exc
        order = await self._orders.get_scoped(parsed, self._account.id)
        if order is None:
            raise OrderNotFoundError(f"Order {order_id} not found")
        return order

    def _fill_price(self, order: Order, quote: MarketQuote) -> Decimal | None:
        """Return an executable price or ``None`` when the order is not eligible."""
        ask = quote.ask if quote.ask is not None else quote.last
        bid = quote.bid if quote.bid is not None else quote.last
        slippage = Decimal(str(self._settings.BROKER_PAPER_SLIPPAGE_BPS))

        if order.order_type is OrderType.MARKET:
            base = ask if order.side is TradeSide.BUY else bid
            return apply_slippage(base, slippage, order.side)

        if order.order_type is OrderType.LIMIT:
            return self._limit_price(order, ask, bid, slippage)

        if order.order_type is OrderType.STOP:
            if not self._stop_triggered(order, quote):
                return None
            base = ask if order.side is TradeSide.BUY else bid
            return apply_slippage(base, slippage, order.side)

        if order.order_type is OrderType.STOP_LIMIT:
            if not self._stop_triggered(order, quote):
                return None
            # After trigger it behaves as a limit order, not a guaranteed fill.
            return self._limit_price(order, ask, bid, slippage)

        return None

    def _limit_price(
        self, order: Order, ask: Decimal, bid: Decimal, slippage: Decimal
    ) -> Decimal | None:
        limit = order.limit_price
        if limit is None:
            return None
        if order.side is TradeSide.BUY:
            if ask > limit:
                return None
            return min(limit, apply_slippage(ask, slippage, TradeSide.BUY))
        if bid < limit:
            return None
        return max(limit, apply_slippage(bid, slippage, TradeSide.SELL))

    @staticmethod
    def _stop_triggered(order: Order, quote: MarketQuote) -> bool:
        stop = order.stop_price
        if stop is None:
            return False
        reference = quote.last
        if order.side is TradeSide.BUY:
            return reference >= stop
        return reference <= stop

    def _fill_quantity(self, remaining: Decimal, *, allow_partial: bool) -> Decimal:
        if not allow_partial or remaining < Decimal("2"):
            return remaining
        ratio = Decimal(str(self._settings.BROKER_PAPER_PARTIAL_FILL_RATIO))
        chunk = (remaining * ratio).to_integral_value(rounding=ROUND_FLOOR)
        if chunk < Decimal("1"):
            chunk = Decimal("1")
        return chunk if chunk < remaining else remaining

    async def _attempt_fill(
        self, order: Order, quote: MarketQuote, *, allow_partial: bool
    ) -> list[Fill]:
        price = self._fill_price(order, quote)
        if price is None:
            # Not eligible yet: remains a working order.
            return []

        remaining = order.quantity - order.filled_quantity
        fill_quantity = self._fill_quantity(remaining, allow_partial=allow_partial)
        if fill_quantity <= 0:
            return []

        if order.side is TradeSide.BUY:
            ok, reason = await self._apply_buy(order, fill_quantity, price)
        else:
            ok, reason = await self._apply_sell(order, fill_quantity, price)

        if not ok:
            assert_transition(order.status, OrderStatus.REJECTED)
            order.status = OrderStatus.REJECTED
            order.error_message = reason
            order.updated_at = datetime.now(UTC)
            await self._session.flush()
            self._emit(
                "order.rejected",
                {"order_id": str(order.id), "symbol": order.symbol, "reason": reason},
            )
            return []

        execution = await self._record_execution(order, fill_quantity, price)
        return [execution]

    async def _apply_buy(
        self, order: Order, quantity: Decimal, price: Decimal
    ) -> tuple[bool, str | None]:
        commission = commission_for(quantity, price, self._flat_commission())
        gross = q(price * quantity)
        total_cost = q(gross + commission)
        cash = Decimal(str(self._account.cash_balance))
        if total_cost > cash:
            return False, "Insufficient funds for order"
        account = await self._accounts.get_locked(self._account.id)
        if account is None:
            return False, "Broker account no longer exists"
        self._account = account
        cash = Decimal(str(account.cash_balance))
        if total_cost > cash:  # re-check after lock
            return False, "Insufficient funds for order"

        account.cash_balance = q(cash - total_cost)
        position = await self._positions.get_open(self._portfolio.id, order.symbol, for_update=True)
        if position is None:
            new_qty, new_basis, new_avg = add_to_position(
                Decimal("0"), Decimal("0"), quantity, price, commission
            )
            position = Position(
                portfolio_id=self._portfolio.id,
                asset_id=order.asset_id,
                symbol=order.symbol,
                side=PositionSide.LONG,
                quantity=new_qty,
                average_entry_price=new_avg,
                cost_basis=new_basis,
                current_price=price,
                market_value=market_value(new_qty, price),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                is_open=True,
                opened_at=datetime.now(UTC),
                last_marked_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self._session.add(position)
            await self._session.flush()
            self._emit(
                "position.created",
                {"position_id": str(position.id), "symbol": order.symbol, "quantity": str(new_qty)},
            )
        else:
            new_qty, new_basis, new_avg = add_to_position(
                position.quantity, position.cost_basis, quantity, price, commission
            )
            position.quantity = new_qty
            position.cost_basis = new_basis
            position.average_entry_price = new_avg
            position.current_price = price
            position.market_value = market_value(new_qty, price)
            position.last_marked_at = datetime.now(UTC)
            position.updated_at = datetime.now(UTC)
            self._emit(
                "position.updated",
                {"position_id": str(position.id), "symbol": order.symbol, "quantity": str(new_qty)},
            )
        await self._session.flush()
        order.fees = q(Decimal(str(order.fees)) + commission)
        order.updated_at = datetime.now(UTC)
        account.updated_at = datetime.now(UTC)
        self._emit(
            "broker.account_updated",
            {"broker_account_id": str(account.id), "cash": str(account.cash_balance)},
        )
        return True, None

    async def _apply_sell(
        self, order: Order, quantity: Decimal, price: Decimal
    ) -> tuple[bool, str | None]:
        position = await self._positions.get_open(self._portfolio.id, order.symbol, for_update=True)
        if position is None or position.quantity < quantity:
            return False, "Insufficient position quantity"
        commission = commission_for(quantity, price, self._flat_commission())
        new_qty, new_basis, realized = reduce_position(
            position.quantity, position.average_entry_price, quantity, price, commission
        )
        account = await self._accounts.get_locked(self._account.id)
        if account is None:
            return False, "Broker account no longer exists"
        self._account = account
        proceeds = q((price * quantity) - commission)
        account.cash_balance = q(Decimal(str(account.cash_balance)) + proceeds)
        account.realized_pnl = q(Decimal(str(account.realized_pnl)) + realized)

        position.quantity = new_qty
        position.cost_basis = new_basis
        position.realized_pnl = q(Decimal(str(position.realized_pnl)) + realized)
        position.current_price = price
        position.market_value = market_value(new_qty, price)
        position.last_marked_at = datetime.now(UTC)
        position.updated_at = datetime.now(UTC)
        if new_qty == 0:
            position.is_open = False
            position.closed_at = datetime.now(UTC)
            self._emit(
                "position.closed",
                {
                    "position_id": str(position.id),
                    "symbol": order.symbol,
                    "realized_pnl": str(realized),
                },
            )
        else:
            self._emit(
                "position.updated",
                {"position_id": str(position.id), "symbol": order.symbol, "quantity": str(new_qty)},
            )
        await self._session.flush()

        order.fees = q(Decimal(str(order.fees)) + commission)
        order.updated_at = datetime.now(UTC)
        account.updated_at = datetime.now(UTC)
        self._emit(
            "broker.account_updated",
            {"broker_account_id": str(account.id), "cash": str(account.cash_balance)},
        )
        return True, None

    async def _record_execution(self, order: Order, quantity: Decimal, price: Decimal) -> Fill:
        commission = commission_for(quantity, price, self._flat_commission())
        gross = q(price * quantity)
        net = q(gross + commission) if order.side is TradeSide.BUY else q(gross - commission)
        executed_at = datetime.now(UTC)
        execution = Execution(
            order_id=order.id,
            quantity=quantity,
            price=price,
            gross_amount=gross,
            net_amount=net,
            fees=commission,
            commission=commission,
            slippage=Decimal("0"),
            broker_execution_id=f"paper-{uuid.uuid4().hex[:16]}",
            executed_at=executed_at,
        )
        self._session.add(execution)

        prior_filled = order.filled_quantity
        new_filled = prior_filled + quantity
        if prior_filled == 0:
            order.average_fill_price = price
        else:
            previous_notional = (order.average_fill_price or Decimal("0")) * prior_filled
            order.average_fill_price = q((previous_notional + gross) / new_filled)
        order.filled_quantity = new_filled

        target = (
            OrderStatus.FILLED if new_filled >= order.quantity else OrderStatus.PARTIALLY_FILLED
        )
        assert_transition(order.status, target)
        order.status = target
        order.updated_at = executed_at
        if target is OrderStatus.FILLED:
            order.filled_at = executed_at
        await self._session.flush()

        self._emit(
            "execution.created",
            {
                "execution_id": str(execution.id),
                "order_id": str(order.id),
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": str(quantity),
                "price": str(price),
                "commission": str(commission),
            },
        )
        self._emit(
            "order.filled" if target is OrderStatus.FILLED else "order.partially_filled",
            {
                "order_id": str(order.id),
                "symbol": order.symbol,
                "side": order.side.value,
                "status": target.value,
                "filled_quantity": str(new_filled),
                "average_fill_price": str(order.average_fill_price),
            },
        )
        return Fill(
            execution_id=execution.id,
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=price,
            gross_amount=gross,
            commission=commission,
            net_amount=net,
            executed_at=executed_at,
        )
