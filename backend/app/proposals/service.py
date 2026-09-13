"""TradeProposal service: creation, evaluation, cancellation, read models.

Execution orchestration lives in :mod:`app.proposals.order_manager`; this service
only creates and risk-evaluates proposals (never submits orders).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.brokers.bootstrap import ensure_paper_account
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.market.services.market_data import MarketDataService
from app.market.validation import normalize_symbol
from app.models.enums import (
    AssetClass,
    NotificationSeverity,
    OrderAction,
    ProposalSource,
    ProposalStatus,
    RiskDecision,
    TradeSide,
)
from app.models.proposal import TradeProposal
from app.models.strategy import StrategySignal
from app.notifications.service import CATEGORY_TRADING, NotificationService
from app.portfolio.service import PortfolioService
from app.proposals.state import EVALUATABLE, assert_transition
from app.proposals.types import ProposalCreate
from app.realtime.events import DomainEvent, queue_event
from app.repositories.proposal import TradeProposalRepository
from app.risk.service import RiskEngine
from app.risk.types import RiskEvaluationResult, RiskRequest

HUNDRED = Decimal("100")


def touch(proposal: TradeProposal, now: datetime) -> None:
    """Set `updated_at` and force it into the UPDATE.

    `updated_at` has a database-side `onupdate`; if we re-assign the same value
    SQLAlchemy drops it from the SET clause and lets the DB generate it, which
    expires the attribute and later raises MissingGreenlet on access.
    """
    proposal.updated_at = now
    flag_modified(proposal, "updated_at")


def action_to_side(action: OrderAction) -> TradeSide:
    return TradeSide.BUY if action is OrderAction.BUY else TradeSide.SELL


def proposal_to_risk_request(proposal: TradeProposal, *, now: datetime) -> RiskRequest:
    return RiskRequest(
        symbol=proposal.symbol,
        side=action_to_side(proposal.action),
        requested_quantity=Decimal(str(proposal.proposed_quantity)),
        entry_price=Decimal(str(proposal.entry_price)) if proposal.entry_price else None,
        stop_loss=Decimal(str(proposal.stop_loss)) if proposal.stop_loss else None,
        take_profit=Decimal(str(proposal.take_profit)) if proposal.take_profit else None,
        strategy_signal_id=proposal.strategy_signal_id,
        strategy_confidence=Decimal(str(proposal.confidence)),
        time_horizon=proposal.time_horizon,
        source=proposal.source.value.lower(),
        timestamp=now,
    )


class ProposalService:
    def __init__(
        self,
        session: AsyncSession,
        market: MarketDataService,
        user,  # noqa: ANN001
        *,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._market = market
        self._user = user
        self._settings = settings or get_settings()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._proposals = TradeProposalRepository(session)

    async def create(
        self,
        payload: ProposalCreate,
        *,
        source: ProposalSource = ProposalSource.MANUAL,
    ) -> TradeProposal:
        if payload.idempotency_key is not None:
            existing = await self._proposals.get_by_idempotency_key(payload.idempotency_key)
            if existing is not None:
                return existing

        symbol = normalize_symbol(payload.symbol)
        asset = await self._market.resolve_asset(symbol)
        if asset is None:
            raise NotFoundError(f"Unknown symbol {symbol}")

        account, portfolio = await ensure_paper_account(self._session, self._user, self._settings)
        quote = await self._market.get_quote(symbol)
        entry = payload.limit_price or payload.stop_price or quote.last
        if payload.quantity is not None:
            quantity = payload.quantity
        elif payload.notional is not None:
            quantity = payload.notional / entry
        else:  # pragma: no cover - validated by schema
            raise ConflictError("quantity or notional is required")

        summary = await PortfolioService(
            self._session, portfolio, self._market, account=account, settings=self._settings
        ).summary()
        position_pct = (
            (quantity * entry) / summary.equity * HUNDRED if summary.equity else Decimal("0")
        )

        signal: StrategySignal | None = None
        if payload.strategy_signal_id is not None:
            signal = await self._session.get(StrategySignal, payload.strategy_signal_id)
            if signal is None:
                raise NotFoundError(f"Strategy signal {payload.strategy_signal_id} not found")

        now = self._clock()
        action = OrderAction.BUY if payload.side is TradeSide.BUY else OrderAction.SELL
        proposal = TradeProposal(
            portfolio_id=portfolio.id,
            strategy_id=signal.strategy_id if signal else None,
            strategy_signal_id=signal.id if signal else None,
            symbol=symbol,
            asset_class=asset.asset_class or AssetClass.EQUITY,
            action=action,
            order_type=payload.order_type,
            source=source,
            status=ProposalStatus.DRAFT,
            proposed_quantity=quantity,
            proposed_position_percentage=position_pct,
            requested_notional=payload.notional,
            entry_price=entry,
            limit_price=payload.limit_price,
            stop_price=payload.stop_price,
            stop_loss=payload.stop_loss,
            take_profit=payload.take_profit,
            confidence=payload.confidence,
            time_horizon=payload.time_horizon,
            reasoning_summary=payload.reasoning_summary,
            market_regime=signal.market_regime if signal else None,
            idempotency_key=payload.idempotency_key,
            expires_at=now + timedelta(seconds=self._settings.TRADE_PROPOSAL_TTL_SECONDS),
            created_at=now,
            updated_at=now,
        )
        await self._proposals.add(proposal)
        self._emit("proposal.created", proposal)
        return proposal

    async def get(self, proposal_id: uuid.UUID) -> TradeProposal | None:
        return await self._proposals.get(proposal_id)

    async def list(
        self, *, status: ProposalStatus | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[TradeProposal], int]:
        _, portfolio = await ensure_paper_account(self._session, self._user, self._settings)
        items = await self._proposals.list_for_portfolio(
            portfolio.id, status=status, limit=limit, offset=offset
        )
        total = await self._proposals.count_for_portfolio(portfolio.id, status=status)
        return items, total

    async def cancel(self, proposal: TradeProposal) -> TradeProposal:
        assert_transition(proposal.status, ProposalStatus.CANCELLED)
        proposal.status = ProposalStatus.CANCELLED
        now = self._clock()
        proposal.decided_at = now
        touch(proposal, now)
        await self._session.flush()
        self._emit("proposal.cancelled", proposal)
        return proposal

    async def evaluate(
        self, proposal: TradeProposal, *, actor: str | None = None
    ) -> tuple[TradeProposal, RiskEvaluationResult]:
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
                raise ConflictError("Proposal has expired")

        if proposal.status not in EVALUATABLE:
            raise ConflictError(f"Proposal in status {proposal.status.value} cannot be evaluated")

        assert_transition(proposal.status, ProposalStatus.PENDING_RISK)
        proposal.status = ProposalStatus.PENDING_RISK
        touch(proposal, now)
        await self._session.flush()

        engine = RiskEngine(self._session, self._market, self._user, settings=self._settings)
        result = await engine.evaluate(
            proposal_to_risk_request(proposal, now=now),
            persist=True,
            actor=actor,
            proposal_id=proposal.id,
        )

        target = (
            ProposalStatus.RISK_REJECTED
            if result.decision in (RiskDecision.REJECTED, RiskDecision.ERROR)
            else ProposalStatus.RISK_APPROVED
        )
        assert_transition(proposal.status, target)
        proposal.status = target
        proposal.decided_at = now
        touch(proposal, now)
        if target is ProposalStatus.RISK_REJECTED:
            proposal.failure_reason = "risk rejected: " + ", ".join(result.reasons)
        await self._session.flush()

        event = (
            "proposal.risk_approved"
            if target is ProposalStatus.RISK_APPROVED
            else "proposal.risk_rejected"
        )
        self._emit(
            event,
            proposal,
            extra={"evaluation_id": str(result.id), "reasons": result.reasons},
        )
        if target is ProposalStatus.RISK_REJECTED:
            await NotificationService(self._session).create_notification(
                user_id=self._user.id,
                category=CATEGORY_TRADING,
                title="Proposal rejected by risk engine",
                message=f"{proposal.symbol} proposal rejected: {', '.join(result.reasons)}",
                severity=NotificationSeverity.WARNING,
                payload={"proposal_id": str(proposal.id)},
            )
        return proposal, result

    def _emit(self, event: str, proposal: TradeProposal, extra: dict | None = None) -> None:
        data = {
            "proposal_id": str(proposal.id),
            "symbol": proposal.symbol,
            "action": proposal.action.value,
            "status": proposal.status.value,
            "source": proposal.source.value,
        }
        if extra:
            data.update(extra)
        queue_event(self._session.info, DomainEvent(event=event, data=data, user_id=self._user.id))
