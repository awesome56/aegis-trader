"""ProposalService: creation, idempotency and risk evaluation."""

from __future__ import annotations

from app.models.enums import ProposalStatus
from app.repositories.proposal import TradeProposalRepository
from app.repositories.risk import RiskEvaluationRepository

from tests.proposals.conftest import proposal_payload


async def test_create_proposal_is_draft_with_market_price(proposal_env) -> None:  # noqa: ANN001
    env = await proposal_env()
    proposal = await env.service.create(proposal_payload())

    assert proposal.status is ProposalStatus.DRAFT
    assert proposal.symbol == "AAPL"
    assert proposal.entry_price is not None
    assert proposal.entry_price > 0
    assert proposal.expires_at is not None
    assert proposal.idempotency_key is None
    assert [e.event for e in env.session.info["pending_events"]][:1] == ["proposal.created"]


async def test_idempotency_key_deduplicates(proposal_env) -> None:  # noqa: ANN001
    env = await proposal_env()
    payload = proposal_payload(idempotency_key="dup-1")
    first = await env.service.create(payload)
    second = await env.service.create(payload)

    assert first.id == second.id
    total = await TradeProposalRepository(env.session).count_for_portfolio(first.portfolio_id)
    assert total == 1


async def test_evaluate_approves_and_persists(proposal_env) -> None:  # noqa: ANN001
    env = await proposal_env()
    proposal = await env.service.create(proposal_payload())
    evaluated, result = await env.service.evaluate(proposal, actor="tester")

    assert evaluated.status is ProposalStatus.RISK_APPROVED
    assert result.id is not None
    rows = await RiskEvaluationRepository(env.session).list_for_proposal(evaluated.id)
    assert len(rows) == 1
    events = [e.event for e in env.session.info["pending_events"]]
    assert "proposal.risk_approved" in events


async def test_low_confidence_is_rejected(proposal_env) -> None:  # noqa: ANN001
    env = await proposal_env()
    proposal = await env.service.create(proposal_payload(confidence="0.1"))
    evaluated, result = await env.service.evaluate(proposal, actor="tester")

    assert evaluated.status is ProposalStatus.RISK_REJECTED
    assert evaluated.failure_reason is not None
    assert result.reasons
    events = [e.event for e in env.session.info["pending_events"]]
    assert "proposal.risk_rejected" in events


async def test_no_stop_loss_is_rejected(proposal_env) -> None:  # noqa: ANN001
    env = await proposal_env()
    proposal = await env.service.create(proposal_payload(stop_loss=None, take_profit=None))
    evaluated, _ = await env.service.evaluate(proposal, actor="tester")

    assert evaluated.status is ProposalStatus.RISK_REJECTED
