"""TradeProposal REST API (Phase 7).

Manual proposals only in V1. Creating a proposal never executes it: the client
must explicitly `evaluate` (Risk Engine) and then `execute` (OrderManager), which
performs a fresh final risk revalidation before any broker submission.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser, DbSession, get_current_user
from app.core.exceptions import NotFoundError
from app.models.enums import ProposalStatus
from app.models.proposal import RiskEvaluation
from app.proposals.dependencies import OrderManagerDep, ProposalServiceDep
from app.proposals.types import ExecutionOutcome, ProposalCreate
from app.repositories.order import ExecutionRepository, OrderRepository
from app.repositories.risk import RiskEvaluationRepository
from app.schemas.broker import BrokerOrderSchema
from app.schemas.proposal import (
    ExecutionSchema,
    ProposalDetailSchema,
    ProposalEvaluationResponse,
    ProposalPageSchema,
    ProposalSchema,
)
from app.schemas.risk import RiskEvaluationSchema

router = APIRouter(
    prefix="/proposals", tags=["proposals"], dependencies=[Depends(get_current_user)]
)


def _detail_orders(orders) -> list[BrokerOrderSchema]:  # noqa: ANN001
    return [BrokerOrderSchema.from_model(order) for order in orders]


@router.post("", response_model=ProposalSchema, status_code=status.HTTP_201_CREATED)
async def create_proposal(
    payload: ProposalCreate,
    service: ProposalServiceDep,
) -> ProposalSchema:
    proposal = await service.create(payload)
    return ProposalSchema.model_validate(proposal)


@router.get("", response_model=ProposalPageSchema)
async def list_proposals(
    service: ProposalServiceDep,
    status_filter: Annotated[ProposalStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProposalPageSchema:
    items, total = await service.list(status=status_filter, limit=limit, offset=offset)
    return ProposalPageSchema(
        items=[ProposalSchema.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{proposal_id}", response_model=ProposalDetailSchema)
async def get_proposal(
    proposal_id: uuid.UUID,
    session: DbSession,
    service: ProposalServiceDep,
) -> ProposalDetailSchema:
    proposal = await service.get(proposal_id)
    if proposal is None:
        raise NotFoundError(f"Proposal {proposal_id} not found")

    evaluations = await RiskEvaluationRepository(session).list_for_proposal(proposal.id)
    orders = await OrderRepository(session).list_by_proposal(proposal.id)
    executions: list[ExecutionSchema] = []
    execution_repo = ExecutionRepository(session)
    for order in orders:
        for execution in await execution_repo.list_for_order(order.id):
            executions.append(ExecutionSchema.model_validate(execution))

    return ProposalDetailSchema(
        proposal=ProposalSchema.model_validate(proposal),
        evaluations=[RiskEvaluationSchema.from_model(row) for row in evaluations],
        orders=_detail_orders(orders),
        executions=executions,
    )


@router.post("/{proposal_id}/evaluate", response_model=ProposalEvaluationResponse)
async def evaluate_proposal(
    proposal_id: uuid.UUID,
    session: DbSession,
    service: ProposalServiceDep,
    user: CurrentUser,
) -> ProposalEvaluationResponse:
    proposal = await service.get(proposal_id)
    if proposal is None:
        raise NotFoundError(f"Proposal {proposal_id} not found")
    proposal, result = await service.evaluate(proposal, actor=user.email)
    evaluation = await session.get(RiskEvaluation, result.id) if result.id else None
    if evaluation is None:
        raise NotFoundError("Risk evaluation was not persisted")
    return ProposalEvaluationResponse(
        proposal=ProposalSchema.model_validate(proposal),
        evaluation=RiskEvaluationSchema.from_model(evaluation),
    )


@router.post("/{proposal_id}/execute", response_model=ExecutionOutcome)
async def execute_proposal(
    proposal_id: uuid.UUID,
    order_manager: OrderManagerDep,
    user: CurrentUser,
) -> ExecutionOutcome:
    return await order_manager.execute(proposal_id, actor=user.email)


@router.post("/{proposal_id}/cancel", response_model=ProposalSchema)
async def cancel_proposal(
    proposal_id: uuid.UUID,
    service: ProposalServiceDep,
) -> ProposalSchema:
    proposal = await service.get(proposal_id)
    if proposal is None:
        raise NotFoundError(f"Proposal {proposal_id} not found")
    proposal = await service.cancel(proposal)
    return ProposalSchema.model_validate(proposal)
