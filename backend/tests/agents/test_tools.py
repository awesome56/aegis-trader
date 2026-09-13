"""Agent tool-layer tests: allowlist, read tools, and the single write tool."""

from __future__ import annotations

from app.agents.enums import AgentRunMode
from app.agents.tools import (
    FORBIDDEN_TOOLS,
    READ_TOOLS,
    WRITE_TOOLS,
    AgentToolContext,
    AgentToolRegistry,
)
from app.core.config import get_settings
from app.models.user import User
from app.repositories.order import OrderRepository
from app.repositories.proposal import TradeProposalRepository


async def _user(session, email: str = "agent-tools@example.com") -> User:
    user = User(email=email, hashed_password="x", is_active=True)
    session.add(user)
    await session.flush()
    return user


def _context(session, user, mode=AgentRunMode.PROPOSE) -> AgentToolContext:
    return AgentToolContext(
        session=session,
        user=user,
        symbol="AAPL",
        timeframe="1h",
        mode=mode,
        settings=get_settings(),
    )


async def test_registry_exposes_only_allowed_tools(db_session) -> None:
    user = await _user(db_session)
    registry = AgentToolRegistry(_context(db_session, user))
    names = {spec.name for spec in registry.specs()}
    assert names <= set(READ_TOOLS) | set(WRITE_TOOLS)
    assert "create_trade_proposal" in names
    for forbidden in FORBIDDEN_TOOLS:
        assert forbidden not in names
        ok, payload, _ = await registry.execute(forbidden, {})
        assert ok is False
        assert payload["error"] == "tool_not_available"


async def test_analysis_only_has_no_write_tool_and_rejects_it(db_session) -> None:
    user = await _user(db_session, "agent-ao@example.com")
    registry = AgentToolRegistry(_context(db_session, user, AgentRunMode.ANALYSIS_ONLY))
    names = {spec.name for spec in registry.specs()}
    assert "create_trade_proposal" not in names
    ok, payload, _ = await registry.execute(
        "create_trade_proposal", {"symbol": "AAPL", "side": "BUY", "quantity": 1}
    )
    assert ok is False
    assert payload["error"] == "proposal_not_permitted"


async def test_read_tools_return_context(db_session) -> None:
    user = await _user(db_session, "agent-read@example.com")
    registry = AgentToolRegistry(_context(db_session, user))

    ok, payload, _ = await registry.execute("get_market_context", {})
    assert ok is True
    assert payload["symbol"] == "AAPL"
    assert "quote" in payload and "regime" in payload

    ok, quote, _ = await registry.execute("get_quote", {"symbol": "AAPL"})
    assert ok is True and quote["symbol"] == "AAPL"

    ok, signals, _ = await registry.execute("get_strategy_signals", {"limit": 5})
    assert ok is True and "signals" in signals

    ok, portfolio, _ = await registry.execute("get_portfolio", {})
    assert ok is True and "equity" in portfolio

    ok, risk, _ = await registry.execute("get_risk_status", {})
    assert ok is True and "trading_state" in risk

    ok, positions, _ = await registry.execute("get_positions", {})
    assert ok is True and "positions" in positions


async def test_create_trade_proposal_is_draft_and_idempotent(db_session) -> None:
    user = await _user(db_session, "agent-propose@example.com")
    registry = AgentToolRegistry(_context(db_session, user))
    args = {
        "symbol": "AAPL",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 1,
        "stop_loss": 1,
        "take_profit": 10000,
        "confidence": 0.9,
        "summary": "evidence aligned",
    }
    ok, payload, _ = await registry.execute(
        "create_trade_proposal", args, idempotency_key="run1:call1"
    )
    assert ok is True
    assert payload["status"] == "DRAFT"

    # Same idempotency key must not create a second proposal.
    ok2, payload2, _ = await registry.execute(
        "create_trade_proposal", args, idempotency_key="run1:call1"
    )
    assert ok2 is True
    assert payload2["proposal_id"] == payload["proposal_id"]

    from app.brokers.bootstrap import ensure_paper_account

    _, portfolio = await ensure_paper_account(db_session, user)
    proposals = await TradeProposalRepository(db_session).list_for_portfolio(portfolio.id)
    assert len(proposals) == 1
    from app.models.enums import ProposalSource

    assert proposals[0].source is ProposalSource.AGENT

    # No execution side effects.
    assert await OrderRepository(db_session).count_for_account(portfolio.broker_account_id) == 0


async def test_invalid_side_rejected(db_session) -> None:
    user = await _user(db_session, "agent-invalid@example.com")
    registry = AgentToolRegistry(_context(db_session, user))
    ok, payload, _ = await registry.execute(
        "create_trade_proposal", {"symbol": "AAPL", "side": "HOLD", "quantity": 1}
    )
    assert ok is False
    assert payload["error"] == "validation_error"
