"""BrokerSafetyGateway (Phase 10).

The only path by which agent-initiated broker writes may reach execution. It
never reproduces RiskEngine math; it enforces permissions and delegates the
financial decision to the existing proposal → RiskEngine → OrderManager chain.

Flow:
    policy permission → trading state/kill switch → (fresh quote) →
    TradeProposal (source=AGENT) → RiskEngine → final revalidation (OrderManager)
    → BrokerAdapter → audit/events → normalized result
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.auto_trading.service import AutoTradingPolicyService
from app.brokers.router import BrokerRouter
from app.core.config import Settings, get_settings
from app.core.exceptions import AegisError
from app.core.logging import get_logger
from app.market.exceptions import MarketDataError
from app.market.services.market_data import MarketDataService
from app.market.validation import detect_asset_class, normalize_symbol
from app.models.broker import BrokerAccount
from app.models.enums import (
    AutoTradeAction,
    NotificationSeverity,
    OrderStatus,
    OrderType,
    ProposalSource,
    ProposalStatus,
    TradeSide,
    TradingState,
)
from app.models.proposal import TradeProposal
from app.models.user import User
from app.notifications.service import NotificationService
from app.proposals.order_manager import OrderManager
from app.proposals.service import ProposalService
from app.proposals.types import ProposalCreate
from app.realtime.events import DomainEvent, queue_event
from app.repositories.broker_account import BrokerAccountRepository
from app.repositories.notification import SystemEventRepository
from app.repositories.order import OrderRepository
from app.risk.trading_state import TradingStateService
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

_RISK_REDUCING = {AutoTradeAction.REDUCE, AutoTradeAction.CLOSE}


@dataclass
class GatewayResult:
    status: str  # EXECUTED | REJECTED
    action: AutoTradeAction
    symbol: str
    environment: str
    approved_quantity: Decimal | None = None
    order_id: uuid.UUID | None = None
    risk_evaluation_id: uuid.UUID | None = None
    reason: str | None = None

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "account_environment": self.environment,
            "symbol": self.symbol,
            "action": self.action.value,
            "approved_quantity": str(self.approved_quantity)
            if self.approved_quantity is not None
            else None,
            "order_id": str(self.order_id) if self.order_id else None,
            "risk_evaluation_id": str(self.risk_evaluation_id)
            if self.risk_evaluation_id
            else None,
            "order_created": self.order_id is not None,
            "reason": self.reason,
        }


class BrokerSafetyGateway:
    def __init__(
        self, session: AsyncSession, user: User, settings: Settings | None = None
    ) -> None:
        self._session = session
        self._user = user
        self._settings = settings or get_settings()
        self._policies = AutoTradingPolicyService(session, self._settings)
        self._market = MarketDataService(session, settings=self._settings)

    async def execute(
        self,
        *,
        account: BrokerAccount,
        action: AutoTradeAction,
        symbol: str,
        side: TradeSide | None = None,
        order_type: OrderType = OrderType.MARKET,
        quantity: Decimal | None = None,
        notional: Decimal | None = None,
        percent: Decimal | None = None,
        limit_price: Decimal | None = None,
        stop_price: Decimal | None = None,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
        strategy_signal_id: uuid.UUID | None = None,
        confidence: Decimal | None = None,
        reason: str | None = None,
        idempotency_key: str | None = None,
        actor: str = "agent",
    ) -> GatewayResult:
        symbol = normalize_symbol(symbol)
        asset_class = detect_asset_class(symbol)

        # Serialise concurrent actions on the same account.
        await BrokerAccountRepository(self._session).get_locked(account.id)

        policy = await self._policies.get_or_create(self._user.id, account)
        permitted, why = self._policies.permits(
            policy, action, symbol=symbol, asset_class=asset_class.value
        )
        if not permitted:
            return await self._reject(action, symbol, account, why or "NOT_PERMITTED")

        state = await TradingStateService(self._session, settings=self._settings).get_or_create()
        if state.trading_state is not TradingState.TRADING_ENABLED:
            return await self._reject(action, symbol, account, "TRADING_STATE")

        if action is AutoTradeAction.CANCEL_ORDER:
            return await self._reject(action, symbol, account, "USE_CANCEL_ORDER")

        return await self._trade(
            account=account,
            action=action,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            notional=notional,
            percent=percent,
            limit_price=limit_price,
            stop_price=stop_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_signal_id=strategy_signal_id,
            confidence=confidence,
            reason=reason,
            idempotency_key=idempotency_key,
            actor=actor,
        )

    # --- trade actions ------------------------------------------------------
    async def _trade(self, **kwargs) -> GatewayResult:  # noqa: ANN003
        account = kwargs["account"]
        action = kwargs["action"]
        symbol = kwargs["symbol"]
        risk_reducing = action in _RISK_REDUCING

        if risk_reducing:
            side, resolved_qty = await self._reducing_side_and_quantity(
                account, symbol, kwargs["side"], kwargs["quantity"], kwargs["percent"]
            )
            if resolved_qty is None or resolved_qty <= 0:
                return await self._reject(action, symbol, account, "NO_POSITION")
        else:
            side = kwargs["side"]
            if side is None:
                return await self._reject(action, symbol, account, "SIDE_REQUIRED")
            resolved_qty = None  # let the proposal derive from quantity/notional

        if not risk_reducing:
            # Risk-increasing actions require a tradable (fresh) quote.
            try:
                await self._market.get_fresh_quote(symbol)
            except MarketDataError as exc:
                return await self._reject(action, symbol, account, f"STALE_MARKET:{exc.code}")

        proposals = ProposalService(
            self._session, self._market, self._user, settings=self._settings
        )
        payload = ProposalCreate(
            symbol=symbol,
            side=side,
            order_type=kwargs["order_type"],
            quantity=resolved_qty if risk_reducing else kwargs["quantity"],
            notional=None if risk_reducing else kwargs["notional"],
            limit_price=kwargs["limit_price"],
            stop_price=kwargs["stop_price"],
            stop_loss=kwargs["stop_loss"],
            take_profit=kwargs["take_profit"],
            strategy_signal_id=kwargs["strategy_signal_id"],
            confidence=kwargs["confidence"] or Decimal("0.5"),
            reasoning_summary=kwargs["reason"],
            idempotency_key=kwargs["idempotency_key"],
        )
        try:
            proposal = await proposals.create(payload, source=ProposalSource.AGENT)
        except AegisError as exc:
            return await self._reject(action, symbol, account, exc.code)

        self._emit("agent.trade_requested", proposal, action, account)

        if proposal.status in (ProposalStatus.EXECUTED,):
            orders = await OrderRepository(self._session).list_by_proposal(proposal.id)
            return GatewayResult(
                status="EXECUTED",
                action=action,
                symbol=symbol,
                environment=account.environment.value,
                approved_quantity=resolved_qty,
                order_id=orders[0].id if orders else None,
                reason="already executed",
            )

        if proposal.status in (
            ProposalStatus.DRAFT,
            ProposalStatus.PENDING,
            ProposalStatus.PENDING_RISK,
        ):
            if risk_reducing:
                # Risk-reducing actions are not blocked by risk limits (e.g. an
                # already-exceeded exposure must still be reducible). The final
                # revalidation in OrderManager is run for audit and permitted via
                # allow_risk_reducing.
                import datetime as _dt

                proposal.status = ProposalStatus.RISK_APPROVED
                proposal.decided_at = _dt.datetime.now(_dt.UTC)
                proposal.updated_at = proposal.decided_at
                await self._session.flush()
            else:
                proposal, evaluation = await proposals.evaluate(proposal, actor=kwargs["actor"])
                if proposal.status is ProposalStatus.RISK_REJECTED:
                    await self._audit(
                        "agent.trade_rejected",
                        proposal,
                        action,
                        account,
                        evaluation.decision.value,
                    )
                    await self._notify(proposal, action, account, "rejected by risk engine")
                    return GatewayResult(
                        status="REJECTED",
                        action=action,
                        symbol=symbol,
                        environment=account.environment.value,
                        risk_evaluation_id=evaluation.id,
                        reason="RISK_REJECTED:" + ",".join(evaluation.reasons[:3]),
                    )

        broker = await BrokerRouter(self._session, self._settings).route(
            user=self._user, account=account
        )
        outcome = await OrderManager(
            self._session, self._market, self._user, broker, settings=self._settings
        ).execute(proposal.id, actor=kwargs["actor"], allow_risk_reducing=risk_reducing)

        if not outcome.executed:
            await self._audit(
                "agent.trade_rejected",
                proposal,
                action,
                account,
                outcome.reason or "EXECUTION_REJECTED",
            )
            return GatewayResult(
                status="REJECTED",
                action=action,
                symbol=symbol,
                environment=account.environment.value,
                reason=outcome.reason or "EXECUTION_REJECTED",
            )

        await self._audit("agent.trade_submitted", proposal, action, account, "submitted")
        await self._notify(proposal, action, account, "executed")
        return GatewayResult(
            status="EXECUTED",
            action=action,
            symbol=symbol,
            environment=account.environment.value,
            approved_quantity=resolved_qty or proposal.proposed_quantity,
            order_id=outcome.order_id,
            risk_evaluation_id=outcome.final_evaluation_id,
        )

    async def _reducing_side_and_quantity(
        self,
        account: BrokerAccount,
        symbol: str,
        side: TradeSide | None,
        quantity: Decimal | None,
        percent: Decimal | None,
    ) -> tuple[TradeSide | None, Decimal | None]:
        broker = await BrokerRouter(self._session, self._settings).route(
            user=self._user, account=account
        )
        position = await broker.get_position(symbol)
        if position is None or Decimal(str(position.quantity)) <= 0:
            return side, None
        existing = Decimal(str(position.quantity))
        closing_side = TradeSide.SELL if str(position.side).upper() == "LONG" else TradeSide.BUY
        if quantity is not None and quantity > 0:
            resolved = min(quantity, existing)
        elif percent is not None and percent > 0:
            resolved = (existing * percent / Decimal("100")).quantize(Decimal("0.0000000001"))
        else:
            resolved = existing
        return closing_side, resolved

    # --- cancel -------------------------------------------------------------
    async def cancel_order(
        self,
        *,
        account: BrokerAccount,
        order_id: uuid.UUID,
        actor: str = "agent",
    ) -> GatewayResult:
        policy = await self._policies.get_or_create(self._user.id, account)
        permitted, why = self._policies.permits(policy, AutoTradeAction.CANCEL_ORDER)
        if not permitted:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.CANCEL_ORDER,
                symbol=str(order_id),
                environment=account.environment.value,
                reason=why or "NOT_PERMITTED",
            )
        state = await TradingStateService(self._session, settings=self._settings).get_or_create()
        if state.trading_state is TradingState.TRADING_ENABLED and not policy.allow_cancel:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.CANCEL_ORDER,
                symbol=str(order_id),
                environment=account.environment.value,
                reason="ACTION_NOT_PERMITTED:CANCEL_ORDER",
            )

        order = await OrderRepository(self._session).get(order_id)
        if order is None or order.broker_account_id != account.id:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.CANCEL_ORDER,
                symbol=str(order_id),
                environment=account.environment.value,
                reason="ORDER_NOT_FOUND",
            )
        terminal = (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        )
        if order.status in terminal:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.CANCEL_ORDER,
                symbol=str(order_id),
                environment=account.environment.value,
                reason="ORDER_NOT_CANCELLABLE",
            )
        if not policy.allow_manage_manual_orders and order.proposal_id is None:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.CANCEL_ORDER,
                symbol=str(order_id),
                environment=account.environment.value,
                reason="MANUAL_ORDER_NOT_MANAGED",
            )

        broker = await BrokerRouter(self._session, self._settings).route(
            user=self._user, account=account
        )
        try:
            result = await broker.cancel_order(order_id)
        except AegisError as exc:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.CANCEL_ORDER,
                symbol=str(order_id),
                environment=account.environment.value,
                reason=exc.code,
            )
        await SystemEventRepository(self._session).record(
            event_type="agent.order_cancel_requested",
            source="auto_trading",
            message=f"Agent cancelled order {order_id}",
            severity=NotificationSeverity.WARNING,
            actor=str(self._user.id),
            payload={"order_id": str(order_id), "environment": account.environment.value},
        )
        return GatewayResult(
            status="EXECUTED" if result.status is OrderStatus.CANCELLED else "REJECTED",
            action=AutoTradeAction.CANCEL_ORDER,
            symbol=str(order_id),
            environment=account.environment.value,
            order_id=order_id,
            reason=None if result.status is OrderStatus.CANCELLED else result.status.value,
        )

    async def replace_order(
        self,
        *,
        account: BrokerAccount,
        order_id: uuid.UUID,
        limit_price: Decimal | None = None,
        stop_price: Decimal | None = None,
        quantity: Decimal | None = None,
        actor: str = "agent",
    ) -> GatewayResult:
        """Replace = validate → cancel existing → (only if cancelled) submit new.

        Never produces duplicate exposure: the replacement is submitted only
        after the original is confirmed cancelled.
        """
        policy = await self._policies.get_or_create(self._user.id, account)
        permitted, why = self._policies.permits(policy, AutoTradeAction.REPLACE_ORDER)
        if not permitted:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.REPLACE_ORDER,
                symbol=str(order_id),
                environment=account.environment.value,
                reason=why or "NOT_PERMITTED",
            )
        state = await TradingStateService(self._session, settings=self._settings).get_or_create()
        if state.trading_state is not TradingState.TRADING_ENABLED:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.REPLACE_ORDER,
                symbol=str(order_id),
                environment=account.environment.value,
                reason="TRADING_STATE",
            )

        order = await OrderRepository(self._session).get(order_id)
        terminal = (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        )
        if order is None or order.broker_account_id != account.id or order.status in terminal:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.REPLACE_ORDER,
                symbol=str(order_id),
                environment=account.environment.value,
                reason="ORDER_NOT_REPLACEABLE",
            )
        if not policy.allow_manage_manual_orders and order.proposal_id is None:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.REPLACE_ORDER,
                symbol=order.symbol,
                environment=account.environment.value,
                reason="MANUAL_ORDER_NOT_MANAGED",
            )

        # Cancel the original directly (governed by the replace permission, not
        # the cancel permission). Do not submit the replacement if cancel fails.
        broker = await BrokerRouter(self._session, self._settings).route(
            user=self._user, account=account
        )
        try:
            cancelled = await broker.cancel_order(order_id)
        except AegisError as exc:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.REPLACE_ORDER,
                symbol=order.symbol,
                environment=account.environment.value,
                reason=f"CANCEL_FAILED:{exc.code}",
            )
        if cancelled.status is not OrderStatus.CANCELLED:
            return GatewayResult(
                status="REJECTED",
                action=AutoTradeAction.REPLACE_ORDER,
                symbol=order.symbol,
                environment=account.environment.value,
                reason=f"CANCEL_FAILED:{cancelled.status.value}",
            )

        # Preserve the original proposal's protective context so the
        # replacement passes the same deterministic risk rules.
        stop_loss = None
        take_profit = None
        confidence = Decimal("0.5")
        strategy_signal_id = None
        if order.proposal_id is not None:
            original_proposal = await self._session.get(TradeProposal, order.proposal_id)
            if original_proposal is not None:
                stop_loss = original_proposal.stop_loss
                take_profit = original_proposal.take_profit
                confidence = original_proposal.confidence
                strategy_signal_id = original_proposal.strategy_signal_id

        replacement = await self.execute(
            account=account,
            action=AutoTradeAction.OPEN,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=quantity or Decimal(str(order.quantity)),
            limit_price=limit_price or order.limit_price,
            stop_price=stop_price or order.stop_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_signal_id=strategy_signal_id,
            confidence=confidence,
            reason=f"replace order {order_id}",
            idempotency_key=f"replace:{order_id}:{limit_price}:{quantity}",
            actor=actor,
        )
        await SystemEventRepository(self._session).record(
            event_type="agent.order_replaced",
            source="auto_trading",
            message=f"Agent replaced order {order_id} -> {replacement.status}",
            severity=NotificationSeverity.INFO,
            actor=str(self._user.id),
            payload={
                "previous_order_id": str(order_id),
                "status": replacement.status,
                "environment": account.environment.value,
            },
        )
        return GatewayResult(
            status=replacement.status,
            action=AutoTradeAction.REPLACE_ORDER,
            symbol=order.symbol,
            environment=account.environment.value,
            approved_quantity=replacement.approved_quantity,
            order_id=replacement.order_id,
            risk_evaluation_id=replacement.risk_evaluation_id,
            reason=replacement.reason,
        )

    # --- helpers ------------------------------------------------------------
    async def _reject(
        self, action: AutoTradeAction, symbol: str, account: BrokerAccount, reason: str
    ) -> GatewayResult:
        logger.info(
            "auto_trade_rejected",
            action=action.value,
            symbol=symbol,
            environment=account.environment.value,
            reason=reason,
        )
        queue_event(
            self._session.info,
            DomainEvent(
                event="agent.trade_rejected",
                data={
                    "symbol": symbol,
                    "action": action.value,
                    "reason": reason,
                    "environment": account.environment.value,
                },
                user_id=self._user.id,
            ),
        )
        return GatewayResult(
            status="REJECTED",
            action=action,
            symbol=symbol,
            environment=account.environment.value,
            reason=reason,
        )

    async def _audit(
        self,
        event_type: str,
        proposal,  # noqa: ANN001
        action: AutoTradeAction,
        account: BrokerAccount,
        detail: str,
    ) -> None:
        await SystemEventRepository(self._session).record(
            event_type=event_type,
            source="auto_trading",
            message=f"Agent {action.value} {proposal.symbol} {detail}",
            severity=NotificationSeverity.INFO,
            actor=str(self._user.id),
            payload={
                "proposal_id": str(proposal.id),
                "symbol": proposal.symbol,
                "action": action.value,
                "environment": account.environment.value,
            },
        )
        self._emit(event_type, proposal, action, account, {"detail": detail})

    def _emit(
        self,
        event: str,
        proposal,  # noqa: ANN001
        action: AutoTradeAction,
        account: BrokerAccount,
        extra: dict | None = None,
    ) -> None:
        data = {
            "proposal_id": str(proposal.id),
            "symbol": proposal.symbol,
            "action": action.value,
            "environment": account.environment.value,
        }
        if extra:
            data.update(extra)
        queue_event(self._session.info, DomainEvent(event=event, data=data, user_id=self._user.id))

    async def _notify(
        self,
        proposal,  # noqa: ANN001
        action: AutoTradeAction,
        account: BrokerAccount,
        outcome: str,
    ) -> None:
        await NotificationService(self._session).create_notification(
            user_id=self._user.id,
            category="TRADING",
            title=f"Autonomous {action.value} {proposal.symbol}",
            message=f"{account.environment.value} account: {outcome}.",
            severity=NotificationSeverity.INFO,
            payload={
                "proposal_id": str(proposal.id),
                "symbol": proposal.symbol,
                "action": action.value,
                "environment": account.environment.value,
            },
        )
