"""TradingAnalysisAgent loop tests using the deterministic FakeLLMProvider."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from app.agents.agent import TradingAnalysisAgent
from app.agents.enums import AgentRunMode
from app.agents.exceptions import AgentLoopLimitError, AgentOutputError
from app.agents.tools import AgentToolContext
from app.ai.types import LLMResponse, LLMToolCall
from app.core.config import get_settings
from app.models.user import User

from tests.ai.fake_provider import FakeLLMProvider


def _response(data: dict) -> LLMResponse:
    return LLMResponse(content=json.dumps(data), provider="fake", model="fake-model")


def _tool_response(name: str, arguments: dict, call_id: str = "call-1") -> LLMResponse:
    return LLMResponse(
        tool_calls=[LLMToolCall(id=call_id, name=name, arguments=arguments)],
        provider="fake",
        model="fake-model",
    )


BASIC = {
    "symbol": "AAPL",
    "action": "BUY",
    "confidence": 0.72,
    "market_regime": "BULLISH",
    "summary": "Trend and momentum aligned.",
    "supporting_evidence": [
        {"type": "strategy_signal", "source": "momentum", "direction": "LONG", "confidence": 0.7}
    ],
    "concerns": ["Earnings soon"],
    "strategy_signals": [],
    "risk_context_summary": "Exposure acceptable.",
    "proposal_recommended": False,
    "proposed_trade": None,
}


async def _user(session, email: str = "agent-loop@example.com") -> User:
    user = User(email=email, hashed_password="x", is_active=True)
    session.add(user)
    await session.flush()
    return user


def _context(session, user, mode=AgentRunMode.ANALYSIS_ONLY) -> AgentToolContext:
    return AgentToolContext(
        session=session,
        user=user,
        symbol="AAPL",
        timeframe="1h",
        mode=mode,
        settings=get_settings(),
    )


async def test_analysis_only_returns_structured_result(db_session) -> None:
    user = await _user(db_session)
    provider = FakeLLMProvider(
        api_key="k", model="fake-model", responses=[_response(BASIC)]
    )
    agent = TradingAnalysisAgent(provider)
    outcome = await agent.run(context=_context(db_session, user), run_key="run-1")
    assert outcome.result.action.value == "BUY"
    assert outcome.result.confidence == Decimal('0.72')
    assert outcome.proposal_id is None
    assert outcome.iterations == 1


async def test_analysis_only_strips_proposal_fields(db_session) -> None:
    user = await _user(db_session, "agent-strip@example.com")
    payload = {
        **BASIC,
        "proposal_recommended": True,
        "proposed_trade": {"side": "BUY", "order_type": "MARKET", "quantity": 1},
    }
    provider = FakeLLMProvider(api_key="k", model="m", responses=[_response(payload)])
    outcome = await TradingAnalysisAgent(provider).run(
        context=_context(db_session, user), run_key="run-2"
    )
    assert outcome.result.proposal_recommended is False
    assert outcome.result.proposed_trade is None


async def test_tool_loop_records_calls(db_session) -> None:
    user = await _user(db_session, "agent-tools-loop@example.com")
    provider = FakeLLMProvider(
        api_key="k",
        model="m",
        responses=[
            _tool_response("get_market_context", {}),
            _response({**BASIC, "action": "HOLD"}),
        ],
    )
    outcome = await TradingAnalysisAgent(provider).run(
        context=_context(db_session, user), run_key="run-3"
    )
    assert outcome.iterations == 2
    assert len(outcome.tool_calls) == 1
    assert outcome.tool_calls[0].name == "get_market_context"
    assert outcome.result.action.value == "HOLD"


async def test_propose_mode_creates_proposal(db_session) -> None:
    user = await _user(db_session, "agent-propose-loop@example.com")
    args = {
        "symbol": "AAPL",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 1,
        "stop_loss": 1,
        "take_profit": 10000,
        "confidence": 0.9,
    }
    provider = FakeLLMProvider(
        api_key="k",
        model="m",
        responses=[
            _tool_response("create_trade_proposal", args, call_id="c1"),
            _response({**BASIC, "proposal_recommended": True}),
        ],
    )
    outcome = await TradingAnalysisAgent(provider).run(
        context=_context(db_session, user, AgentRunMode.PROPOSE), run_key="run-4"
    )
    assert outcome.proposal_id is not None

    from app.repositories.proposal import TradeProposalRepository

    proposals = await TradeProposalRepository(db_session).list_for_portfolio(
        await _portfolio_id(db_session, user)
    )
    assert len(proposals) == 1


async def _portfolio_id(session, user) -> object:
    from app.brokers.bootstrap import ensure_paper_account

    _, portfolio = await ensure_paper_account(session, user)
    return portfolio.id


async def test_invalid_structured_output_raises(db_session) -> None:
    user = await _user(db_session, "agent-bad-json@example.com")
    provider = FakeLLMProvider(
        api_key="k",
        model="m",
        responses=[LLMResponse(content="not json", provider="fake", model="m")],
    )
    with pytest.raises(AgentOutputError):
        await TradingAnalysisAgent(provider).run(
            context=_context(db_session, user), run_key="run-5"
        )


async def test_tool_loop_limit_raises(db_session) -> None:
    user = await _user(db_session, "agent-loop-limit@example.com")
    settings = get_settings().model_copy(update={"AGENT_MAX_TOOL_ITERATIONS": 2})
    provider = FakeLLMProvider(
        api_key="k",
        model="m",
        responses=[
            _tool_response("get_quote", {"symbol": "AAPL"}, f"c{i}") for i in range(5)
        ],
    )
    with pytest.raises(AgentLoopLimitError):
        await TradingAnalysisAgent(provider, settings).run(
            context=_context(db_session, user), run_key="run-6"
        )
