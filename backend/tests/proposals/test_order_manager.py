"""OrderManager: final revalidation, price guard, broker linkage, events."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from app.core.exceptions import ConflictError
from app.models.enums import OrderType, ProposalStatus, TradingState
from app.repositories.order import OrderRepository

from tests.proposals.conftest import proposal_payload


async def _approved(env):  # noqa: ANN001
    proposal = await env.service.create(proposal_payload())
    proposal, _ = await env.service.evaluate(proposal, actor="tester")
    assert proposal.status is ProposalStatus.RISK_APPROVED
    return proposal


async def test_execute_links_order_and_marks_executed(proposal_env) -> None:  # noqa: ANN001
    env = await proposal_env()
    proposal = await _approved(env)

    outcome = await env.manager.execute(proposal.id, actor="tester")

    assert outcome.executed is True
    assert outcome.order_id is not None
    assert outcome.status == ProposalStatus.EXECUTED.value
    orders = await OrderRepository(env.session).list_by_proposal(proposal.id)
    assert len(orders) == 1
    assert orders[0].proposal_id == proposal.id
    events = [e.event for e in env.session.info["pending_events"]]
    assert "proposal.execution_started" in events
    assert "proposal.executed" in events


async def test_execute_is_idempotent_for_executed_proposal(proposal_env) -> None:  # noqa: ANN001
    env = await proposal_env()
    proposal = await _approved(env)
    first = await env.manager.execute(proposal.id)
    second = await env.manager.execute(proposal.id)

    assert first.order_id == second.order_id
    orders = await OrderRepository(env.session).list_by_proposal(proposal.id)
    assert len(orders) == 1


async def test_execute_unapproved_is_rejected(proposal_env) -> None:  # noqa: ANN001
    env = await proposal_env()
    proposal = await env.service.create(proposal_payload())

    with pytest.raises(ConflictError):
        await env.manager.execute(proposal.id)


async def test_execute_expired_proposal(proposal_env) -> None:  # noqa: ANN001
    env = await proposal_env()
    proposal = await _approved(env)
    proposal.expires_at = env.now - timedelta(seconds=1)
    await env.session.flush()

    outcome = await env.manager.execute(proposal.id)

    assert outcome.executed is False
    assert outcome.status == ProposalStatus.EXPIRED.value


async def test_final_revalidation_blocks_when_kill_switch_tripped(proposal_env) -> None:  # noqa: ANN001
    from app.risk.trading_state import TradingStateService

    env = await proposal_env()
    proposal = await _approved(env)
    await TradingStateService(env.session, settings=env.settings).transition(
        TradingState.TRADING_DISABLED, reason="test halt", actor="tester"
    )

    outcome = await env.manager.execute(proposal.id)

    assert outcome.executed is False
    assert outcome.status == ProposalStatus.FAILED.value
    assert "revalidation" in (outcome.reason or "")


async def test_price_deviation_guard_blocks_execution(proposal_env) -> None:  # noqa: ANN001
    env = await proposal_env(EXECUTION_MAX_PRICE_DEVIATION_BPS=1.0)
    proposal = await env.service.create(
        proposal_payload(
            order_type=OrderType.LIMIT,
            limit_price=Decimal("50"),
            stop_loss=Decimal("45"),
            take_profit=Decimal("65"),
        )
    )
    proposal, _ = await env.service.evaluate(proposal, actor="tester")

    outcome = await env.manager.execute(proposal.id)

    assert outcome.executed is False
    assert outcome.status == ProposalStatus.FAILED.value
    assert "price moved" in (outcome.reason or "")
