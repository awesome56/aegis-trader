"""Risk Engine REST API.

Exposes risk overview, settings, evaluations, an evaluation-only simulation
endpoint (never executes) and the persisted trading-state (kill switch) controls.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import CurrentUser, DbSession, get_current_user
from app.brokers.bootstrap import ensure_paper_account
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.market.dependencies import MarketDataDep
from app.models.enums import NotificationSeverity, TradingState
from app.models.risk import RiskSettings
from app.notifications.service import CATEGORY_RISK, NotificationService
from app.portfolio.service import PortfolioService
from app.realtime.events import DomainEvent, queue_event
from app.repositories.notification import SystemEventRepository
from app.repositories.order import OrderRepository
from app.repositories.risk import RiskEvaluationRepository
from app.risk.dependencies import RiskEngineDep, RiskSettingsDep, TradingStateDep
from app.risk.status import status_from_utilization_rows, utilization_rows
from app.risk.types import RiskRequest
from app.schemas.risk import (
    RiskEvaluationPageSchema,
    RiskEvaluationSchema,
    RiskEventSchema,
    RiskOverviewSchema,
    RiskRequestSchema,
    RiskSettingsSchema,
    RiskSettingsUpdateSchema,
    RiskUtilizationSchema,
    TradingActionRequest,
    TradingStatusSchema,
)

router = APIRouter(prefix="/risk", tags=["risk"], dependencies=[Depends(get_current_user)])


def _settings_schema(row: RiskSettings) -> RiskSettingsSchema:
    return RiskSettingsSchema.model_validate(row, from_attributes=True)


def _trading_schema(row) -> TradingStatusSchema:  # noqa: ANN001
    from app.models.enums import TradingState as _State

    return TradingStatusSchema(
        trading_state=_State(row.trading_state),
        previous_state=_State(row.previous_state) if row.previous_state else None,
        reason=row.reason,
        actor=row.actor,
        changed_at=row.changed_at,
    )


def _evaluation_schema(row) -> RiskEvaluationSchema:  # noqa: ANN001
    from app.models.enums import TradeSide

    return RiskEvaluationSchema(
        id=row.id,
        decision=row.decision,
        symbol=row.symbol or "",
        side=TradeSide(row.side) if row.side else TradeSide.BUY,
        source=row.source,
        requested_quantity=row.requested_quantity or Decimal("0"),
        approved_quantity=row.approved_quantity,
        requested_notional=row.requested_notional or Decimal("0"),
        approved_notional=row.approved_notional,
        entry_price=row.entry_price,
        stop_loss=row.stop_loss,
        take_profit=row.take_profit,
        estimated_risk_amount=row.estimated_risk_amount,
        risk_reward_ratio=row.risk_reward_ratio,
        portfolio_exposure_before_percent=row.portfolio_exposure_before_pct or Decimal("0"),
        portfolio_exposure_after_percent=row.portfolio_exposure_after_pct,
        risk_score=row.risk_score,
        rules=row.checks or [],
        reasons=row.reasons or [],
        warnings=row.warnings or [],
        evaluated_at=row.evaluated_at,
    )


@router.get("", response_model=RiskOverviewSchema, summary="Risk overview")
async def get_risk_overview(
    session: DbSession,
    user: CurrentUser,
    market: MarketDataDep,
    settings_service: RiskSettingsDep,
    trading_state: TradingStateDep,
) -> RiskOverviewSchema:
    settings = get_settings()
    account, portfolio = await ensure_paper_account(session, user, settings)
    portfolio_service = PortfolioService(
        session, portfolio, market, account=account, settings=settings
    )
    summary = await portfolio_service.summary()
    drawdown = await portfolio_service.drawdown_percent()
    limits = settings_service.to_snapshot(await settings_service.get_or_create(user.id))
    state = await trading_state.get_or_create()
    trades_today = await OrderRepository(session).count_created_since(
        account.id, datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    rows = utilization_rows(
        limits=limits,
        equity=summary.equity,
        exposure_percent=summary.exposure_percent,
        open_positions=summary.position_count,
        trades_today=trades_today,
        drawdown_percent=drawdown,
        daily_pnl=summary.daily_pnl,
        warning=Decimal(str(settings.RISK_WARNING_UTILIZATION_PERCENT)),
        critical=Decimal(str(settings.RISK_CRITICAL_UTILIZATION_PERCENT)),
    )
    return RiskOverviewSchema(
        status=status_from_utilization_rows(rows),
        trading_state=TradingState(state.trading_state),
        equity=summary.equity,
        cash=summary.cash,
        buying_power=summary.buying_power,
        portfolio_exposure_percent=summary.exposure_percent,
        daily_pnl=summary.daily_pnl,
        daily_loss_limit_percent=limits.max_daily_loss_percent,
        current_drawdown_percent=drawdown,
        max_drawdown_percent=limits.max_drawdown_percent,
        open_positions=summary.position_count,
        max_open_positions=limits.max_open_positions,
        trades_today=trades_today,
        max_trades_per_day=limits.max_trades_per_day,
        utilizations=[RiskUtilizationSchema.model_validate(row) for row in rows],
        updated_at=datetime.now(UTC),
    )


@router.get("/settings", response_model=RiskSettingsSchema, summary="Get risk settings")
async def get_settings_route(
    session: DbSession, user: CurrentUser, settings_service: RiskSettingsDep
) -> RiskSettingsSchema:
    return _settings_schema(await settings_service.get_or_create(user.id))


@router.put("/settings", response_model=RiskSettingsSchema, summary="Update risk settings")
async def update_settings_route(
    payload: RiskSettingsUpdateSchema,
    session: DbSession,
    user: CurrentUser,
    settings_service: RiskSettingsDep,
) -> RiskSettingsSchema:
    data = payload.model_dump(exclude_unset=True)
    if "unknown_sector_policy" in data and data["unknown_sector_policy"] not in {
        "reject",
        "allow",
        "warn",
    }:
        raise ValidationError("unknown_sector_policy must be reject|allow|warn")
    row = await settings_service.get_or_create(user.id)
    await settings_service.update(row, data)
    await SystemEventRepository(session).record(
        event_type="risk.settings_updated",
        source="risk",
        message="Risk settings updated",
        severity=NotificationSeverity.WARNING,
        actor=str(user.id),
        payload={"fields": sorted(data)},
    )
    queue_event(
        session.info,
        DomainEvent(event="risk.settings_updated", data={"fields": sorted(data)}, user_id=user.id),
    )
    return _settings_schema(row)


@router.get(
    "/evaluations", response_model=RiskEvaluationPageSchema, summary="List risk evaluations"
)
async def list_evaluations(
    session: DbSession,
    user: CurrentUser,
    market: MarketDataDep,
    decision: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> RiskEvaluationPageSchema:
    _, portfolio = await ensure_paper_account(session, user, get_settings())
    repo = RiskEvaluationRepository(session)
    rows = await repo.list_evaluations(
        portfolio_id=portfolio.id,
        symbol=symbol,
        decision=decision,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    total = await repo.count_evaluations(
        portfolio_id=portfolio.id, symbol=symbol, decision=decision
    )
    return RiskEvaluationPageSchema(
        items=[_evaluation_schema(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=RiskEvaluationSchema,
    summary="Risk evaluation detail",
)
async def get_evaluation(
    evaluation_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> RiskEvaluationSchema:
    _, portfolio = await ensure_paper_account(session, user, get_settings())
    row = await RiskEvaluationRepository(session).get(evaluation_id)
    if row is None or row.portfolio_id != portfolio.id:
        raise NotFoundError(f"Risk evaluation {evaluation_id} not found")
    return _evaluation_schema(row)


@router.get("/events", response_model=list[RiskEventSchema], summary="Recent risk events")
async def list_events(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[RiskEventSchema]:
    events = await SystemEventRepository(session).list_events(event_type_prefix="risk", limit=limit)
    return [RiskEventSchema.model_validate(event) for event in events]


@router.post(
    "/evaluate", response_model=RiskEvaluationSchema, summary="Evaluate a hypothetical trade"
)
async def evaluate(
    payload: RiskRequestSchema, engine: RiskEngineDep, session: DbSession
) -> RiskEvaluationSchema:
    """Deterministic evaluation only — never submits an order."""
    request = RiskRequest(**payload.model_dump(), source="manual")
    result = await engine.evaluate(request)
    return RiskEvaluationSchema(**result.model_dump())


@router.get("/trading-status", response_model=TradingStatusSchema, summary="Trading status")
async def trading_status(trading_state: TradingStateDep) -> TradingStatusSchema:
    return _trading_schema(await trading_state.get_or_create())


async def _transition(
    *,
    target: TradingState,
    payload: TradingActionRequest,
    session: DbSession,
    user: CurrentUser,
    trading_state: TradingStateDep,
    notify: bool,
) -> TradingStatusSchema:
    if not payload.confirm:
        raise ValidationError("This action requires confirm=true")
    row = await trading_state.transition(
        target, reason=payload.reason or "manual", actor=str(user.id)
    )
    await SystemEventRepository(session).record(
        event_type="risk.trading_state_changed",
        source="risk",
        message=f"Trading state changed to {target.value}",
        severity=(
            NotificationSeverity.CRITICAL
            if target is TradingState.EMERGENCY_STOP
            else NotificationSeverity.WARNING
        ),
        actor=str(user.id),
        payload={"trading_state": target.value, "reason": row.reason},
    )
    if notify:
        await NotificationService(session).create_notification(
            user_id=user.id,
            category=CATEGORY_RISK,
            title="Trading state changed",
            message=f"System trading state is now {target.value}.",
            severity=(
                NotificationSeverity.CRITICAL
                if target is TradingState.EMERGENCY_STOP
                else NotificationSeverity.WARNING
            ),
            payload={"trading_state": target.value},
        )
    return _trading_schema(row)


@router.post("/pause", response_model=TradingStatusSchema, summary="Pause new trading")
async def pause(
    payload: TradingActionRequest,
    session: DbSession,
    user: CurrentUser,
    trading_state: TradingStateDep,
) -> TradingStatusSchema:
    return await _transition(
        target=TradingState.TRADING_PAUSED,
        payload=payload,
        session=session,
        user=user,
        trading_state=trading_state,
        notify=True,
    )


@router.post("/resume", response_model=TradingStatusSchema, summary="Resume trading")
async def resume(
    payload: TradingActionRequest,
    session: DbSession,
    user: CurrentUser,
    trading_state: TradingStateDep,
) -> TradingStatusSchema:
    return await _transition(
        target=TradingState.TRADING_ENABLED,
        payload=payload,
        session=session,
        user=user,
        trading_state=trading_state,
        notify=True,
    )


@router.post("/enable", response_model=TradingStatusSchema, summary="Enable trading")
async def enable(
    payload: TradingActionRequest,
    session: DbSession,
    user: CurrentUser,
    trading_state: TradingStateDep,
) -> TradingStatusSchema:
    return await _transition(
        target=TradingState.TRADING_ENABLED,
        payload=payload,
        session=session,
        user=user,
        trading_state=trading_state,
        notify=False,
    )


@router.post("/disable", response_model=TradingStatusSchema, summary="Disable new trading")
async def disable(
    payload: TradingActionRequest,
    session: DbSession,
    user: CurrentUser,
    trading_state: TradingStateDep,
) -> TradingStatusSchema:
    return await _transition(
        target=TradingState.TRADING_DISABLED,
        payload=payload,
        session=session,
        user=user,
        trading_state=trading_state,
        notify=True,
    )


@router.post(
    "/emergency-stop", response_model=TradingStatusSchema, summary="Activate emergency stop"
)
async def emergency_stop(
    payload: TradingActionRequest,
    session: DbSession,
    user: CurrentUser,
    trading_state: TradingStateDep,
) -> TradingStatusSchema:
    return await _transition(
        target=TradingState.EMERGENCY_STOP,
        payload=payload,
        session=session,
        user=user,
        trading_state=trading_state,
        notify=True,
    )
