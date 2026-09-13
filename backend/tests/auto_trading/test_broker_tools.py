"""Dynamic broker tool availability (Phase 10).

Write tools are exposed only when the account policy permits them, and every
write routes through BrokerSafetyGateway.
"""

from __future__ import annotations

from app.agents.enums import AgentRunMode
from app.agents.tools import (
    BROKER_WRITE_TOOL_ACTIONS,
    FORBIDDEN_TOOLS,
    AgentToolContext,
    AgentToolRegistry,
)
from app.brokers.bootstrap import ensure_paper_account
from app.core.config import get_settings
from app.models.user import User


async def _user(session, email: str = "tools-auto@example.com") -> User:
    user = User(email=email, hashed_password="x", is_active=True)
    session.add(user)
    await session.flush()
    return user


def _context(session, user, account_id, actions: set[str]) -> AgentToolContext:
    return AgentToolContext(
        session=session,
        user=user,
        symbol="AAPL",
        timeframe="1h",
        mode=AgentRunMode.PROPOSE,
        settings=get_settings(),
        broker_account_id=account_id,
        auto_actions=frozenset(actions),
    )


async def test_write_tools_gated_by_action_permissions(db_session) -> None:
    user = await _user(db_session)
    account, _ = await ensure_paper_account(db_session, user)

    # No auto actions -> no broker write tools exposed.
    registry = AgentToolRegistry(_context(db_session, user, account.id, set()))
    names = {spec.name for spec in registry.specs()}
    assert "broker_get_account" in names  # read tools always available
    for tool in BROKER_WRITE_TOOL_ACTIONS:
        assert tool not in names

    # OPEN only -> open tool exposed, cancel not.
    registry = AgentToolRegistry(_context(db_session, user, account.id, {"OPEN"}))
    names = {spec.name for spec in registry.specs()}
    assert "broker_open_position" in names
    assert "broker_cancel_order" not in names
    assert "broker_close_position" not in names

    # Calling a non-permitted write tool is rejected.
    ok, payload, _ = await registry.execute("broker_close_position", {"symbol": "AAPL"})
    assert ok is False
    assert payload["error"] == "auto_trading_not_permitted"

    # Forbidden execution-style tools never exist.
    for forbidden in FORBIDDEN_TOOLS:
        ok, payload, _ = await registry.execute(forbidden, {})
        assert ok is False and payload["error"] == "tool_not_available"


async def test_broker_read_tool_returns_account_state(db_session) -> None:
    user = await _user(db_session, "tools-read@example.com")
    account, _ = await ensure_paper_account(db_session, user)
    registry = AgentToolRegistry(_context(db_session, user, account.id, set()))
    ok, payload, _ = await registry.execute("broker_get_account", {})
    assert ok is True
    assert "cash" in payload or "buying_power" in payload
