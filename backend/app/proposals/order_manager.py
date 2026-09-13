"""OrderManager: the authoritative execution orchestrator.

Pipeline (Phase 7): proposal state checks → row lock → EXECUTING transition →
**final** risk revalidation (fresh state) → price-deviation check → build a
normalized BrokerOrderRequest → BrokerAdapter.submit_order → link the broker
Order to the proposal → persist status/audit → publish events.

It never trusts a prior RiskEvaluation: market/portfolio state may have changed.
BrokerAdapter and RiskEngine never import this module.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.base import BrokerAdapter
from app.brokers.types import BrokerOrderRequest
from app.core.config import Settings, get_settings
from app.core.exceptions import AegisError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.market.services.market_data import MarketDataService
from app.models.enums import NotificationSeverity, ProposalStatus, RiskDecision
from app.models.proposal import TradeProposal
from app.notifications.service import CATEGORY_TRADING, NotificationService
from app.proposals.service import action_to_side, proposal_to_risk_request, touch
from app.proposals.state import EXECUTABLE, assert_transition
from app.proposals.types import ExecutionOutcome
from app.realtime.events import DomainEvent, queue_event
from app.repositories.order import OrderRepository
from app.repositories.proposal import TradeProposalRepository
from app.risk.service import RiskEngine

logger = get_logger(__name__)

BPS = Decimal("10000")
_APPROVED = {RiskDecision.APPROVED, RiskDecision.APPROVED_WITH_WARNINGS}
_SUBMITTED_STATUSES = {"CREATED", "SUBMITTED", "ACCEPTED", "PARTIALLY_FILLED", "FILLED"}


class OrderManager:
    def __init__(
        self,
        session: AsyncSession,
        market: MarketDataService,
        user,  # noqa: ANN001
        broker: BrokerAdapter,
        *,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._market = market
        self._user = user
        self._broker = broker
        self._settings = settings or get_settings()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._proposals = TradeProposalRepository(session)
        self._orders = OrderRepository(session)

    async def execute(
        self,
        proposal_id: uuid.UUID,
        *,
        actor: str | None = None,
        allow_risk_reducing: bool = False,
    ) -> ExecutionOutcome:
        proposal = await self._proposals.get_locked(proposal_id)
        if proposal is None:
            raise NotFoundError(f"Proposal {proposal_id} not found")

        # Idempotent: an already-executed proposal returns its linked order.
        if proposal.status is ProposalStatus.EXECUTED:
            orders = await self._orders.list_by_proposal(proposal.id)
            return ExecutionOutcome(
                proposal_id=proposal.id,
                executed=True,
                status=proposal.status.value,
                order_id=orders[0].id if orders else None,
                reason="proposal already executed",
            )

        if proposal.status not in EXECUTABLE:
            raise ConflictError(
                f"Proposal in status {proposal.status.value} cannot be executed"
            )

        now = self._clock()
        if proposal.expires_at is not None:
            expires = proposal.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if expires <= now:
                assert_transition(proposal.status, ProposalStatus.EXPIRED)
                proposal.status = ProposalStatus.EXPIRED
                proposal.decided_at = now
                touch(proposal, now)
                await self._session.flush()
                self._emit("proposal.failed", proposal, extra={"reason": "expired"})
                return ExecutionOutcome(
                    proposal_id=proposal.id,
                    executed=False,
                    status=proposal.status.value,
                    reason="proposal expired",
                )

        assert_transition(proposal.status, ProposalStatus.EXECUTING)
        proposal.status = ProposalStatus.EXECUTING
        touch(proposal, now)
        await self._session.flush()
        self._emit("proposal.execution_started", proposal)

        engine = RiskEngine(self._session, self._market, self._user, settings=self._settings)
        final = await engine.evaluate(
            proposal_to_risk_request(proposal, now=now),
            persist=True,
            actor=actor,
            proposal_id=proposal.id,
        )
        if (
            self._settings.EXECUTION_REQUIRE_FINAL_RISK_REVALIDATION
            and final.decision not in _APPROVED
            and not allow_risk_reducing
        ):
            return await self._fail(
                proposal,
                f"final risk revalidation rejected: {', '.join(final.reasons)}",
                final_evaluation_id=final.id,
                final_decision=final.decision.value,
            )
        if allow_risk_reducing and final.decision not in _APPROVED:
            # Risk-reducing actions (reduce/close) are allowed to proceed even
            # when a risk limit is already exceeded; the revalidation is still
            # recorded for audit. Trading-state/kill-switch checks still apply.
            logger.warning(
                "risk_reducing_override",
                proposal_id=str(proposal.id),
                decision=final.decision.value,
            )

        # Price-movement guard: do not submit an old proposal at a very different price.
        max_bps = Decimal(str(self._settings.EXECUTION_MAX_PRICE_DEVIATION_BPS))
        quote = await self._market.get_quote(proposal.symbol)
        reference = Decimal(str(proposal.entry_price)) if proposal.entry_price else None
        if reference and max_bps > 0:
            side = action_to_side(proposal.action)
            top_of_book = quote.bid or quote.last
            executable = (quote.ask or top_of_book) if side.value == "BUY" else top_of_book
            executable = executable or quote.last
            deviation = abs(executable - reference) / reference * BPS
            if deviation > max_bps:
                return await self._fail(
                    proposal,
                    f"price moved {deviation:.1f}bps beyond the {max_bps}bps execution limit",
                    final_evaluation_id=final.id,
                    final_decision=final.decision.value,
                )

        broker_request = BrokerOrderRequest(
            symbol=proposal.symbol,
            side=action_to_side(proposal.action),
            order_type=proposal.order_type,
            quantity=Decimal(str(proposal.proposed_quantity)),
            limit_price=Decimal(str(proposal.limit_price)) if proposal.limit_price else None,
            stop_price=Decimal(str(proposal.stop_price)) if proposal.stop_price else None,
            client_order_id=f"proposal-{proposal.id}",
            idempotency_key=f"proposal-{proposal.id}",
        )
        try:
            result = await self._broker.submit_order(broker_request)
        except AegisError as exc:
            return await self._fail(
                proposal,
                f"broker error: {exc.message}",
                final_evaluation_id=final.id,
                final_decision=final.decision.value,
            )

        order = await self._orders.get(result.order_id)
        if order is not None:
            order.proposal_id = proposal.id
            order.updated_at = now
            await self._session.flush()

        if result.status.value in _SUBMITTED_STATUSES:
            assert_transition(proposal.status, ProposalStatus.EXECUTED)
            proposal.status = ProposalStatus.EXECUTED
            proposal.executed_at = now
            touch(proposal, now)
            await self._session.flush()
            self._emit(
                "proposal.executed",
                proposal,
                extra={"order_id": str(result.order_id), "order_status": result.status.value},
            )
            await NotificationService(self._session).create_notification(
                user_id=self._user.id,
                category=CATEGORY_TRADING,
                title="Proposal executed",
                message=f"{proposal.symbol} {proposal.action.value} order {result.status.value}",
                severity=NotificationSeverity.INFO,
                payload={"proposal_id": str(proposal.id), "order_id": str(result.order_id)},
            )
            return ExecutionOutcome(
                proposal_id=proposal.id,
                executed=True,
                status=proposal.status.value,
                order_id=result.order_id,
                final_evaluation_id=final.id,
                final_decision=final.decision.value,
            )

        return await self._fail(
            proposal,
            result.error_message or f"broker returned {result.status.value}",
            final_evaluation_id=final.id,
            final_decision=final.decision.value,
        )

    async def _fail(
        self,
        proposal: TradeProposal,
        reason: str,
        *,
        final_evaluation_id: uuid.UUID | None,
        final_decision: str | None,
    ) -> ExecutionOutcome:
        if proposal.status is ProposalStatus.EXECUTING:
            assert_transition(proposal.status, ProposalStatus.FAILED)
        proposal.status = ProposalStatus.FAILED
        proposal.failure_reason = reason
        touch(proposal, self._clock())
        await self._session.flush()
        self._emit("proposal.failed", proposal, extra={"reason": reason})
        await NotificationService(self._session).create_notification(
            user_id=self._user.id,
            category=CATEGORY_TRADING,
            title="Proposal execution failed",
            message=f"{proposal.symbol}: {reason}",
            severity=NotificationSeverity.WARNING,
            payload={"proposal_id": str(proposal.id)},
        )
        return ExecutionOutcome(
            proposal_id=proposal.id,
            executed=False,
            status=proposal.status.value,
            final_evaluation_id=final_evaluation_id,
            final_decision=final_decision,
            reason=reason,
        )

    def _emit(self, event: str, proposal: TradeProposal, extra: dict | None = None) -> None:
        data = {
            "proposal_id": str(proposal.id),
            "symbol": proposal.symbol,
            "action": proposal.action.value,
            "status": proposal.status.value,
        }
        if extra:
            data.update(extra)
        queue_event(self._session.info, DomainEvent(event=event, data=data, user_id=self._user.id))
