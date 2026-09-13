"""Deterministic Risk Engine.

Builds a read-only :class:`RiskContext`, runs independent rules, computes the
maximum permissible size, persists a :class:`RiskEvaluation` and publishes
events. It never submits orders, mutates positions/cash, or reserves funds.

Concurrency note: evaluation alone cannot guarantee funds/exposure remain
unchanged before a later execution. Phase 7 must revalidate critical rules
immediately before order submission using the same engine.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.brokers.bootstrap import ensure_paper_account
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.market.domain.models import MarketQuote
from app.market.services.market_data import MarketDataService
from app.market.validation import normalize_symbol
from app.models.enums import NotificationSeverity, RiskDecision
from app.models.proposal import RiskEvaluation
from app.models.user import User
from app.notifications.service import CATEGORY_RISK, NotificationService
from app.portfolio.service import PortfolioService
from app.realtime.events import DomainEvent, queue_event
from app.repositories.asset import AssetRepository
from app.repositories.order import OrderRepository
from app.repositories.risk import RiskEvaluationRepository
from app.risk.enums import RuleSeverity
from app.risk.rules import default_rules
from app.risk.settings_service import RiskSettingsService
from app.risk.sizing import build_plan, compute_caps, resolve_entry_price
from app.risk.trading_state import TradingStateService
from app.risk.types import RiskContext, RiskEvaluationResult, RiskRequest, RuleResult

logger = get_logger(__name__)

HUNDRED = Decimal("100")
CRITICAL_RULE_KEYS = {"trading_state", "max_daily_loss", "max_drawdown"}


class RiskEngine:
    def __init__(
        self,
        session: AsyncSession,
        market: MarketDataService,
        user: User,
        *,
        settings: Settings | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._market = market
        self._user = user
        self._settings = settings or get_settings()
        self._clock: Callable[[], datetime] = clock or (lambda: datetime.now(UTC))
        self._settings_service = RiskSettingsService(session, self._settings)
        self._evaluations = RiskEvaluationRepository(session)
        self._orders = OrderRepository(session)
        self._assets = AssetRepository(session)

    async def evaluate(
        self,
        request: RiskRequest,
        *,
        persist: bool = True,
        actor: str | None = None,
        proposal_id: UUID | None = None,
    ) -> RiskEvaluationResult:
        now = self._clock()
        symbol = normalize_symbol(request.symbol)
        limits = self._settings_service.to_snapshot(
            await self._settings_service.get_or_create(self._user.id)
        )

        account, portfolio = await ensure_paper_account(self._session, self._user, self._settings)
        portfolio_service = PortfolioService(
            self._session,
            portfolio,
            self._market,
            account=account,
            settings=self._settings,
            clock=self._clock,
        )
        summary = await portfolio_service.summary()
        valuations = await portfolio_service.positions()
        drawdown = await portfolio_service.drawdown_percent()

        position = next((item for item in valuations if item.symbol == symbol), None)
        symbol_exposure_value = position.market_value if position else Decimal("0")
        symbol_exposure_percent = position.weight_percent if position else Decimal("0")
        existing_quantity = position.quantity if position else Decimal("0")

        asset = await self._assets.get_by_symbol(symbol)
        sector = (position.sector if position else None) or (asset.sector if asset else None)
        asset_class = (position.asset_class if position else None) or (
            asset.asset_class.value if asset else None
        )
        sector_value = (
            sum((item.market_value for item in valuations if item.sector == sector), Decimal("0"))
            if sector
            else Decimal("0")
        )
        asset_class_value = (
            sum(
                (item.market_value for item in valuations if item.asset_class == asset_class),
                Decimal("0"),
            )
            if asset_class
            else Decimal("0")
        )

        quote, quote_is_stale, quote_detail = await self._freshness(symbol)
        entry = resolve_entry_price(request, quote)
        caps = compute_caps(
            request=request,
            limits=limits,
            equity=summary.equity,
            buying_power=summary.buying_power,
            portfolio_market_value=summary.market_value,
            symbol_exposure_value=symbol_exposure_value,
            sector_exposure_value=sector_value,
            asset_class_exposure_value=asset_class_value,
            existing_quantity=existing_quantity,
            entry=entry,
        )
        plan = build_plan(
            request=request,
            caps=caps,
            entry=entry,
            equity=summary.equity,
            portfolio_market_value=summary.market_value,
            symbol_exposure_value=symbol_exposure_value,
        )

        state_row = await TradingStateService(
            self._session, settings=self._settings, clock=self._clock
        ).get_or_create()
        trades_today = await self._orders.count_created_since(
            account.id, now.replace(hour=0, minute=0, second=0, microsecond=0)
        )

        context = RiskContext(
            request=request,
            trading_state=state_row.trading_state,
            limits=limits,
            currency=summary.currency,
            equity=summary.equity,
            cash=summary.cash,
            buying_power=summary.buying_power,
            portfolio_market_value=summary.market_value,
            portfolio_exposure_percent=summary.exposure_percent,
            symbol_exposure_value=symbol_exposure_value,
            symbol_exposure_percent=symbol_exposure_percent,
            has_existing_position=position is not None,
            open_positions=summary.position_count,
            sector=sector,
            sector_exposure_value=sector_value,
            asset_class=asset_class,
            asset_class_exposure_value=asset_class_value,
            daily_pnl=summary.daily_pnl,
            drawdown_percent=drawdown,
            trades_today=trades_today,
            quote=quote,
            quote_is_stale=quote_is_stale,
            quote_detail=quote_detail,
            evaluated_at=now,
            size_caps=caps,
        )

        results = [rule.evaluate(context) for rule in default_rules()]
        blocking_failed = _failed(results, RuleSeverity.BLOCKING)
        warning_failed = _failed(results, RuleSeverity.WARNING)

        if not limits.is_enabled:
            decision = RiskDecision.ERROR
            approved_quantity: Decimal | None = None
        elif blocking_failed:
            decision = RiskDecision.REJECTED
            approved_quantity = None
        else:
            decision = (
                RiskDecision.APPROVED_WITH_WARNINGS if warning_failed else RiskDecision.APPROVED
            )
            approved_quantity = plan.approved_quantity

        approved_notional = (approved_quantity * entry) if approved_quantity and entry else None
        risk_per_unit = abs(entry - request.stop_loss) if entry and request.stop_loss else None
        estimated_risk = (
            approved_quantity * risk_per_unit
            if approved_quantity is not None and risk_per_unit is not None
            else None
        )
        risk_reward = _risk_reward(entry, request)
        risk_score = _risk_score(results)
        reasons = [result.key.upper() for result in blocking_failed]
        warnings = [result.key.upper() for result in warning_failed]

        evaluation_id = None
        if persist:
            model = RiskEvaluation(
                proposal_id=proposal_id,
                portfolio_id=portfolio.id,
                strategy_signal_id=request.strategy_signal_id,
                decision=decision,
                source=request.source,
                symbol=symbol,
                side=request.side,
                requested_quantity=plan.requested_quantity,
                requested_notional=plan.requested_notional,
                entry_price=entry,
                stop_loss=request.stop_loss,
                take_profit=request.take_profit,
                estimated_risk_amount=estimated_risk,
                risk_score=risk_score,
                approved_quantity=approved_quantity,
                approved_notional=approved_notional,
                approved_position_percentage=(
                    approved_notional / summary.equity * HUNDRED
                    if approved_notional is not None and summary.equity
                    else None
                ),
                risk_reward_ratio=risk_reward,
                portfolio_exposure_before_pct=summary.exposure_percent,
                portfolio_exposure_after_pct=plan.projected_exposure_percent,
                checks=[result.model_dump(mode="json") for result in results],
                reasons=reasons,
                warnings=warnings,
                settings_snapshot=limits.model_dump(mode="json"),
                evaluated_by="risk_engine",
                evaluated_at=now,
                created_at=now,
                updated_at=now,
            )
            self._session.add(model)
            await self._session.flush()
            evaluation_id = model.id

        result = RiskEvaluationResult(
            id=evaluation_id,
            decision=decision,
            symbol=symbol,
            side=request.side,
            source=request.source,
            requested_quantity=plan.requested_quantity,
            approved_quantity=approved_quantity,
            requested_notional=plan.requested_notional,
            approved_notional=approved_notional,
            entry_price=entry,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            estimated_risk_amount=estimated_risk,
            risk_reward_ratio=risk_reward,
            portfolio_exposure_before_percent=summary.exposure_percent,
            portfolio_exposure_after_percent=plan.projected_exposure_percent,
            risk_score=risk_score,
            rules=results,
            reasons=reasons,
            warnings=warnings,
            evaluated_at=now,
        )
        await self._publish(result, blocking_failed)
        logger.info(
            "risk_evaluation",
            evaluation_id=str(evaluation_id),
            symbol=symbol,
            side=request.side.value,
            decision=decision.value,
            requested=str(plan.requested_quantity),
            approved=str(approved_quantity),
            failed_rules=reasons,
            exposure=str(summary.exposure_percent),
            trading_state=state_row.trading_state.value,
        )
        return result

    async def _freshness(self, symbol: str) -> tuple[MarketQuote | None, bool, str | None]:
        try:
            quote = await self._market.get_quote(symbol)
        except Exception as exc:  # noqa: BLE001 - report unavailable, fail closed
            return None, True, str(exc)
        assessment = self._market.freshness.assess_quote(quote)
        return (
            quote,
            assessment.is_stale or assessment.market_closed,
            f"age_seconds={assessment.age_seconds:.1f} session={assessment.session}",
        )

    async def _publish(self, result: RiskEvaluationResult, blocking: list[RuleResult]) -> None:
        payload = {
            "evaluation_id": str(result.id) if result.id else None,
            "symbol": result.symbol,
            "side": result.side.value,
            "decision": result.decision.value,
            "requested_quantity": str(result.requested_quantity),
            "approved_quantity": str(result.approved_quantity)
            if result.approved_quantity is not None
            else None,
            "reasons": result.reasons,
        }
        queue_event(self._session.info, DomainEvent(event="risk.evaluation_created", data=payload))
        critical = [item for item in blocking if item.key in CRITICAL_RULE_KEYS]
        if result.decision is RiskDecision.REJECTED and critical:
            queue_event(
                self._session.info,
                DomainEvent(
                    event="risk.critical",
                    data={**payload, "rule_keys": [item.key for item in critical]},
                ),
            )
            await NotificationService(self._session).create_notification(
                user_id=self._user.id,
                category=CATEGORY_RISK,
                title="Critical risk threshold reached",
                message=(
                    f"{result.symbol} evaluation rejected: "
                    + ", ".join(item.key for item in critical)
                ),
                severity=NotificationSeverity.CRITICAL,
                payload={"evaluation_id": str(result.id) if result.id else None},
            )
        elif result.decision is RiskDecision.REJECTED:
            queue_event(self._session.info, DomainEvent(event="risk.warning", data=payload))


def _failed(results: list[RuleResult], severity: RuleSeverity) -> list[RuleResult]:
    return [result for result in results if not result.passed and result.severity is severity]


def _risk_reward(entry: Decimal | None, request: RiskRequest) -> Decimal | None:
    if entry is None or request.stop_loss is None or request.take_profit is None:
        return None
    risk = abs(entry - request.stop_loss)
    reward = abs(request.take_profit - entry)
    if risk <= 0:
        return None
    return (reward / risk).quantize(Decimal("0.000001"))


def _risk_score(results: list[RuleResult]) -> Decimal:
    if not results:
        return Decimal("0")
    passed = sum(1 for result in results if result.passed)
    return (Decimal(passed) / Decimal(len(results))).quantize(Decimal("0.000001"))
