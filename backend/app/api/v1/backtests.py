"""Backtesting REST API (authenticated, owner-scoped).

Backtests are pure simulation: creating/running one never touches paper/live
broker, orders, positions, cash or risk state.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser, DbSession, get_current_user
from app.backtesting.service import BacktestService
from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.backtest import Backtest, BacktestResult
from app.models.enums import BacktestStatus
from app.repositories.strategy import StrategyRepository
from app.schemas.backtest import (
    BacktestCreateRequest,
    BacktestMetricsSchema,
    BacktestPageSchema,
    BacktestResultSchema,
    BacktestSchema,
    BacktestTradeSchema,
    DrawdownPointSchema,
    EquityCurvePointSchema,
)
from app.workers.enqueue import enqueue_backtest

router = APIRouter(
    prefix="/backtests", tags=["backtests"], dependencies=[Depends(get_current_user)]
)


def _summary(
    backtest: Backtest, strategy_name: str | None, result: BacktestResult | None
) -> BacktestSchema:
    return BacktestSchema(
        id=backtest.id,
        strategy_id=backtest.strategy_id,
        strategy_name=strategy_name,
        name=backtest.name,
        symbols=list(backtest.symbols or []),
        timeframe=backtest.timeframe,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        initial_capital=backtest.initial_capital,
        benchmark_symbol=backtest.benchmark_symbol,
        status=backtest.status,
        created_at=backtest.created_at,
        started_at=backtest.started_at,
        completed_at=backtest.completed_at,
        error=backtest.error,
        final_capital=result.final_capital if result else None,
        total_return_pct=result.total_return_pct if result else None,
        max_drawdown_pct=result.max_drawdown_pct if result else None,
        num_trades=result.num_trades if result else None,
    )


async def _start(session, service: BacktestService, user, backtest: Backtest) -> None:
    """Enqueue on the worker; fall back to inline execution if Redis is absent."""
    gate = get_settings()
    if not gate.BACKTEST_ENABLED:
        raise ConflictError("Backtesting is disabled")
    enqueued = await enqueue_backtest(backtest.id)
    _ = user
    if not enqueued:
        await service.execute(backtest.id)


@router.get("", response_model=BacktestPageSchema, summary="List backtests")
async def list_backtests(
    session: DbSession,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> BacktestPageSchema:
    service = BacktestService(session)
    items, total = await service.list(user.id, limit=page_size, offset=(page - 1) * page_size)
    strategies = {row.id: row.name for row in await StrategyRepository(session).list_all()}
    schemas = []
    for backtest in items:
        result = await service.result_for(backtest.id)
        schemas.append(_summary(backtest, strategies.get(backtest.strategy_id), result))
    return BacktestPageSchema(items=schemas, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=BacktestSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create + run a backtest",
)
async def create_backtest(
    payload: BacktestCreateRequest,
    session: DbSession,
    user: CurrentUser,
) -> BacktestSchema:
    service = BacktestService(session)
    backtest = await service.create(
        user_id=user.id,
        strategy_id=payload.strategy_id,
        symbols=payload.symbols,
        timeframe=payload.timeframe,
        start_date=payload.start_date,
        end_date=payload.end_date,
        initial_capital=payload.initial_capital,
        position_size_percent=payload.position_size_percent,
        fees_pct=payload.fees_pct,
        slippage_pct=payload.slippage_pct,
        benchmark_symbol=payload.benchmark_symbol,
        force_close_at_end=payload.force_close_at_end,
        name=payload.name,
    )
    await _start(session, service, user, backtest)
    result = await service.result_for(backtest.id)
    return _summary(backtest, await service.strategy_name(backtest.strategy_id), result)


@router.get("/{backtest_id}", response_model=BacktestSchema, summary="Backtest detail")
async def get_backtest(
    backtest_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> BacktestSchema:
    service = BacktestService(session)
    backtest = await service.get(user.id, backtest_id)
    result = await service.result_for(backtest.id)
    return _summary(backtest, await service.strategy_name(backtest.strategy_id), result)


@router.get("/{backtest_id}/result", response_model=BacktestResultSchema, summary="Backtest result")
async def get_backtest_result(
    backtest_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> BacktestResultSchema:
    service = BacktestService(session)
    backtest = await service.get(user.id, backtest_id)
    result = await service.result_for(backtest.id)
    if result is None:
        if backtest.status in (BacktestStatus.PENDING, BacktestStatus.RUNNING):
            raise ConflictError("backtest result is not ready yet")
        raise NotFoundError("backtest has no result")

    metrics = (
        BacktestMetricsSchema(**result.metrics)
        if result.metrics
        else BacktestMetricsSchema(
            initial_capital=result.initial_capital,
            final_capital=result.final_capital,
            net_profit=result.final_capital - result.initial_capital,
            total_return_pct=result.total_return_pct,
            benchmark_return_pct=result.benchmark_return_pct,
            num_trades=result.num_trades,
            wins=result.wins,
            losses=result.losses,
            win_rate=result.win_rate,
            average_win=result.average_win,
            average_loss=result.average_loss,
            largest_win=result.average_win,
            largest_loss=result.average_loss,
            gross_profit=result.average_win * result.wins,
            gross_loss=result.average_loss * result.losses,
            profit_factor=result.profit_factor,
            expectancy=result.expectancy or 0,
            max_drawdown=result.max_drawdown_pct,
            max_drawdown_pct=result.max_drawdown_pct,
            sharpe_ratio=result.sharpe_ratio,
            sortino_ratio=result.sortino_ratio,
            total_fees=result.fees,
            total_slippage=result.slippage,
            average_holding_seconds=0,
            exposure_pct=result.exposure_pct or 0,
        )
    )
    equity = [
        EquityCurvePointSchema(**_normalise_point(point))
        for point in (result.equity_curve or [])
    ]
    return BacktestResultSchema(
        backtest_id=backtest.id,
        engine_version=result.engine_version,
        strategy_config=result.strategy_config,
        metrics=metrics,
        equity_curve=equity,
        drawdown_curve=[
            DrawdownPointSchema(timestamp=point.timestamp, drawdown_pct=point.drawdown_pct)
            for point in equity
        ],
        monthly_returns=list(result.monthly_returns or []),
        trades=[BacktestTradeSchema(**trade) for trade in (result.trade_history or [])],
    )


@router.post("/{backtest_id}/run", response_model=BacktestSchema, summary="Run a queued backtest")
async def run_backtest(
    backtest_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> BacktestSchema:
    service = BacktestService(session)
    backtest = await service.get(user.id, backtest_id)
    if backtest.status is BacktestStatus.RUNNING:
        raise ConflictError("backtest is already running")
    if backtest.status is BacktestStatus.COMPLETED:
        raise ConflictError("backtest already completed")
    if backtest.status is BacktestStatus.CANCELLED:
        raise ConflictError("backtest was cancelled")
    await _start(session, service, user, backtest)
    result = await service.result_for(backtest.id)
    return _summary(backtest, await service.strategy_name(backtest.strategy_id), result)


@router.post(
    "/{backtest_id}/cancel",
    response_model=BacktestSchema,
    summary="Cancel a pending backtest",
)
async def cancel_backtest(
    backtest_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> BacktestSchema:
    service = BacktestService(session)
    backtest = await service.cancel(user.id, backtest_id)
    return _summary(backtest, await service.strategy_name(backtest.strategy_id), None)


def _normalise_point(point: dict) -> dict:
    if "positions_value" not in point or "cumulative_return_pct" not in point:
        raise ValidationError("stored equity curve is malformed")
    return point
