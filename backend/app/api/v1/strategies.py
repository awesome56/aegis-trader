"""Strategy REST API (analytical only — never trades).

Strategy rows are global templates; any authenticated user may view them and
toggle enabled state. Enabling/disabling only changes whether the strategy is
evaluated — it never executes, cancels or alters any order or position.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import CurrentUser, DbSession, get_current_user
from app.core.exceptions import NotFoundError
from app.models.enums import NotificationSeverity, SignalDirection
from app.models.strategy import Strategy, StrategySignal
from app.repositories.notification import SystemEventRepository
from app.schemas.strategy import (
    EvaluateRequest,
    SignalEvidenceSchema,
    SignalPageSchema,
    SignalSchema,
    StrategyDetailSchema,
    StrategyEvaluationSchema,
    StrategySchema,
)
from app.strategies.dependencies import StrategyDep

router = APIRouter(
    prefix="/strategies",
    tags=["strategies"],
    dependencies=[Depends(get_current_user)],
)

RECENT_SIGNALS = 10


def _strategy_schema(strategy: Strategy, count: int, last: object) -> StrategySchema:
    return StrategySchema(
        id=strategy.id,
        key=strategy.slug,
        name=strategy.name,
        description=strategy.description,
        strategy_type=strategy.strategy_type,
        is_enabled=strategy.is_enabled,
        timeframe=strategy.timeframe,
        priority=strategy.priority,
        parameters=strategy.parameters,
        asset_classes=strategy.asset_classes,
        signal_count=count,
        last_signal_at=last,  # type: ignore[arg-type]
        created_at=strategy.created_at,
        updated_at=strategy.updated_at,
    )


def _signal_schema(signal: StrategySignal, strategy: Strategy | None = None) -> SignalSchema:
    return SignalSchema(
        id=signal.id,
        strategy_id=signal.strategy_id,
        strategy_key=strategy.slug if strategy else None,
        strategy_name=strategy.name if strategy else None,
        symbol=signal.symbol,
        direction=signal.direction,
        strength=signal.strength,
        confidence=signal.confidence,
        price=signal.price,
        timeframe=signal.timeframe,
        time_horizon=signal.time_horizon,
        market_regime=signal.market_regime,
        indicators=signal.indicators,
        signal_time=signal.signal_time,
        data_timestamp=signal.data_timestamp,
        expires_at=signal.expires_at,
    )


@router.get("", response_model=list[StrategySchema], summary="List strategies")
async def list_strategies(service: StrategyDep) -> list[StrategySchema]:
    result: list[StrategySchema] = []
    for strategy in await service.list_strategies():
        count, last = await service.strategy_stats(strategy.id)
        result.append(_strategy_schema(strategy, count, last))
    return result


@router.get("/signals", response_model=SignalPageSchema, summary="List strategy signals")
async def list_signals(
    service: StrategyDep,
    strategy_id: Annotated[uuid.UUID | None, Query()] = None,
    symbol: Annotated[str | None, Query()] = None,
    timeframe: Annotated[str | None, Query()] = None,
    direction: Annotated[SignalDirection | None, Query()] = None,
    start: Annotated[datetime | None, Query(description="ISO 8601 start")] = None,
    end: Annotated[datetime | None, Query(description="ISO 8601 end")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SignalPageSchema:
    signals = await service.list_signals(
        strategy_id=strategy_id,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        start=start,
        end=end,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    total = await service.count_signals(
        strategy_id=strategy_id,
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        start=start,
        end=end,
    )
    strategies = {strategy.id: strategy for strategy in await service.list_strategies()}
    return SignalPageSchema(
        items=[_signal_schema(signal, strategies.get(signal.strategy_id)) for signal in signals],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{strategy_id}", response_model=StrategyDetailSchema, summary="Strategy detail")
async def get_strategy(strategy_id: uuid.UUID, service: StrategyDep) -> StrategyDetailSchema:
    strategy = await service.get_strategy(strategy_id)
    if strategy is None:
        raise NotFoundError(f"Strategy {strategy_id} not found")
    count, last = await service.strategy_stats(strategy.id)
    recent = await service.list_signals(strategy_id=strategy.id, limit=RECENT_SIGNALS)
    base = _strategy_schema(strategy, count, last)
    return StrategyDetailSchema(
        **base.model_dump(),
        recent_signals=[_signal_schema(signal, strategy) for signal in recent],
    )


@router.get(
    "/{strategy_id}/signals", response_model=SignalPageSchema, summary="Signals for a strategy"
)
async def strategy_signals(
    strategy_id: uuid.UUID,
    service: StrategyDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SignalPageSchema:
    strategy = await service.get_strategy(strategy_id)
    if strategy is None:
        raise NotFoundError(f"Strategy {strategy_id} not found")
    signals = await service.list_signals(
        strategy_id=strategy.id, limit=page_size, offset=(page - 1) * page_size
    )
    total = await service.count_signals(strategy_id=strategy.id)
    return SignalPageSchema(
        items=[_signal_schema(signal, strategy) for signal in signals],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{strategy_id}/enable", response_model=StrategySchema, summary="Enable strategy")
async def enable_strategy(
    strategy_id: uuid.UUID, service: StrategyDep, session: DbSession, user: CurrentUser
) -> StrategySchema:
    strategy = await service.get_strategy(strategy_id)
    if strategy is None:
        raise NotFoundError(f"Strategy {strategy_id} not found")
    await service.set_enabled(strategy, True)
    await SystemEventRepository(session).record(
        event_type="strategy.enabled",
        source="strategies",
        message=f"Strategy {strategy.slug} enabled",
        severity=NotificationSeverity.INFO,
        actor=str(user.id),
        payload={"strategy_id": str(strategy.id), "slug": strategy.slug},
    )
    count, last = await service.strategy_stats(strategy.id)
    return _strategy_schema(strategy, count, last)


@router.post("/{strategy_id}/disable", response_model=StrategySchema, summary="Disable strategy")
async def disable_strategy(
    strategy_id: uuid.UUID, service: StrategyDep, session: DbSession, user: CurrentUser
) -> StrategySchema:
    strategy = await service.get_strategy(strategy_id)
    if strategy is None:
        raise NotFoundError(f"Strategy {strategy_id} not found")
    await service.set_enabled(strategy, False)
    await SystemEventRepository(session).record(
        event_type="strategy.disabled",
        source="strategies",
        message=f"Strategy {strategy.slug} disabled",
        severity=NotificationSeverity.INFO,
        actor=str(user.id),
        payload={"strategy_id": str(strategy.id), "slug": strategy.slug},
    )
    count, last = await service.strategy_stats(strategy.id)
    return _strategy_schema(strategy, count, last)


@router.post(
    "/evaluate",
    response_model=list[StrategyEvaluationSchema],
    summary="Evaluate strategies on demand (analytical only)",
)
async def evaluate_strategies(
    payload: EvaluateRequest, service: StrategyDep
) -> list[StrategyEvaluationSchema]:
    results = await service.evaluate(
        payload.symbol,
        payload.timeframe,
        strategy_ids=payload.strategy_ids,
        persist=True,
    )
    schemas: list[StrategyEvaluationSchema] = []
    for result in results:
        signal = None
        if result.signal is not None:
            signal = SignalEvidenceSchema(
                strategy_key=result.signal.strategy_key,
                strategy_name=result.signal.strategy_name,
                symbol=result.signal.symbol,
                direction=result.signal.direction,
                strength=result.signal.strength,
                confidence=result.signal.confidence,
                price=result.signal.indicators.get("price"),
                timeframe=result.signal.timeframe,
                time_horizon=result.signal.time_horizon,
                market_regime=result.signal.regime,
                indicators=result.signal.indicators,
                generated_at=result.signal.generated_at,
                data_timestamp=result.signal.data_timestamp,
                expires_at=result.signal.expires_at,
            )
        schemas.append(
            StrategyEvaluationSchema(
                strategy_key=result.strategy_key,
                strategy_name=result.strategy_name,
                symbol=result.symbol,
                timeframe=result.timeframe,
                status=result.status,
                reason=result.reason,
                signal=signal,
            )
        )
    return schemas
