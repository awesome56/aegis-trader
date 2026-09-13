"""TradingAnalysisAgent REST API (Phase 9C).

Runs are analysis/propose only. There is no execution endpoint here and the
agent has no execution capability.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.agents.service import AgentService
from app.auth.dependencies import CurrentUser, DbSession, get_current_user
from app.core.config import get_settings
from app.core.exceptions import ConflictError
from app.models.agent import AgentDecision, AgentRun
from app.schemas.agent import (
    AgentDecisionPageSchema,
    AgentDecisionSchema,
    AgentRunCreateRequest,
    AgentRunPageSchema,
    AgentRunSchema,
    AgentStatusSchema,
)
from app.workers.enqueue import enqueue_agent_run

router = APIRouter(prefix="/agent", tags=["agent"], dependencies=[Depends(get_current_user)])


def _run_schema(run: AgentRun) -> AgentRunSchema:
    return AgentRunSchema(
        id=run.id,
        status=run.status,
        provider=run.provider,
        model=run.model,
        mode=run.mode,
        symbols=list(run.symbols or []),
        prompt=run.prompt,
        error=run.error,
        latency_ms=run.latency_ms,
        tokens_used=run.tokens_used,
        usage=run.usage,
        proposal_id=run.proposal_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
    )


def _decision_schema(decision: AgentDecision) -> AgentDecisionSchema:
    return AgentDecisionSchema(
        id=decision.id,
        agent_run_id=decision.agent_run_id,
        symbol=decision.symbol,
        action=decision.action,
        confidence=decision.confidence,
        reasoning_summary=decision.reasoning_summary,
        evidence=decision.evidence,
        concerns=decision.concerns,
        proposal_recommended=decision.proposal_recommended,
        market_regime=decision.market_regime,
        strategy_signal_ids=decision.strategy_signal_ids,
        proposal_id=decision.proposal_id,
        created_at=decision.created_at,
    )


@router.get("/status", response_model=AgentStatusSchema, summary="Agent status")
async def agent_status(session: DbSession, user: CurrentUser) -> AgentStatusSchema:
    return AgentStatusSchema(**await AgentService(session).status(user.id))


@router.get("/runs", response_model=AgentRunPageSchema, summary="List agent runs")
async def list_runs(
    session: DbSession,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AgentRunPageSchema:
    items, total = await AgentService(session).list_runs(
        user.id, limit=page_size, offset=(page - 1) * page_size
    )
    return AgentRunPageSchema(
        items=[_run_schema(run) for run in items], total=total, page=page, page_size=page_size
    )


@router.post(
    "/runs",
    response_model=AgentRunSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create + run an agent analysis",
)
async def create_run(
    payload: AgentRunCreateRequest, session: DbSession, user: CurrentUser
) -> AgentRunSchema:
    if not get_settings().AGENT_ENABLED:
        raise ConflictError("the agent is disabled")
    service = AgentService(session)
    run = await service.create_run(
        user_id=user.id,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        mode=payload.mode,
        provider_config_id=payload.provider_config_id,
        question=payload.prompt,
    )
    enqueued = await enqueue_agent_run(run.id)
    if not enqueued:
        run = await service.execute(run.id)
    return _run_schema(run)


@router.get("/runs/{run_id}", response_model=AgentRunSchema, summary="Agent run detail")
async def get_run(run_id: uuid.UUID, session: DbSession, user: CurrentUser) -> AgentRunSchema:
    return _run_schema(await AgentService(session).get_run(user.id, run_id))


@router.get("/decisions", response_model=AgentDecisionPageSchema, summary="List agent decisions")
async def list_decisions(
    session: DbSession,
    user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AgentDecisionPageSchema:
    items, total = await AgentService(session).list_decisions(
        user.id, limit=page_size, offset=(page - 1) * page_size
    )
    return AgentDecisionPageSchema(
        items=[_decision_schema(d) for d in items], total=total, page=page, page_size=page_size
    )


@router.get(
    "/decisions/{decision_id}", response_model=AgentDecisionSchema, summary="Agent decision detail"
)
async def get_decision(
    decision_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> AgentDecisionSchema:
    return _decision_schema(await AgentService(session).get_decision(user.id, decision_id))
