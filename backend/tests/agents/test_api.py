"""Agent REST API tests (analysis-only + propose, no execution)."""

from __future__ import annotations

import json

from app.ai.types import LLMResponse, LLMToolCall
from httpx import AsyncClient

from tests.ai.fake_provider import fake_factory

AI_BASE = "/api/v1/ai/providers"
AGENT_BASE = "/api/v1/agent"

ANALYSIS = {
    "symbol": "AAPL",
    "action": "BUY",
    "confidence": 0.7,
    "market_regime": "BULLISH",
    "summary": "Aligned evidence.",
    "supporting_evidence": [
        {"type": "strategy_signal", "source": "momentum", "direction": "LONG", "confidence": 0.7}
    ],
    "concerns": [],
    "strategy_signals": [],
    "risk_context_summary": "ok",
    "proposal_recommended": False,
    "proposed_trade": None,
}


def _final() -> LLMResponse:
    return LLMResponse(content=json.dumps(ANALYSIS), provider="fake", model="fake-model")


def _proposal_call() -> LLMResponse:
    return LLMResponse(
        tool_calls=[
            LLMToolCall(
                id="c1",
                name="create_trade_proposal",
                arguments={
                    "symbol": "AAPL",
                    "side": "BUY",
                    "order_type": "MARKET",
                    "quantity": 1,
                    "stop_loss": 1,
                    "take_profit": 10000,
                    "confidence": 0.9,
                },
            )
        ],
        provider="fake",
        model="fake-model",
    )


async def _configure_provider(client: AsyncClient) -> None:
    created = await client.post(
        AI_BASE, json={"provider": "openai", "model": "gpt-4o-mini", "api_key": "sk-test-1234"}
    )
    assert created.status_code == 201, created.text


async def test_agent_status_and_auth(client: AsyncClient) -> None:
    assert (await client.get(f"{AGENT_BASE}/status")).status_code == 401


async def test_analysis_only_run(authenticated_client: AsyncClient, monkeypatch) -> None:
    await _configure_provider(authenticated_client)
    monkeypatch.setattr("app.agents.service.create_provider", fake_factory(responses=[_final()]))

    created = await authenticated_client.post(
        f"{AGENT_BASE}/runs",
        json={"symbol": "AAPL", "timeframe": "1h", "mode": "ANALYSIS_ONLY"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "COMPLETED"
    assert body["mode"] == "ANALYSIS_ONLY"
    assert body["proposal_id"] is None

    decisions = await authenticated_client.get(f"{AGENT_BASE}/decisions")
    assert decisions.status_code == 200
    items = decisions.json()["items"]
    assert items and items[0]["action"] == "BUY"
    assert items[0]["proposal_recommended"] is False

    status = await authenticated_client.get(f"{AGENT_BASE}/status")
    assert status.status_code == 200
    assert status.json()["provider"] == "openai"
    assert status.json()["runs_today"] >= 1


async def test_propose_run_creates_draft_proposal_only(
    authenticated_client: AsyncClient, monkeypatch
) -> None:
    await _configure_provider(authenticated_client)
    monkeypatch.setattr(
        "app.agents.service.create_provider",
        fake_factory(responses=[_proposal_call(), _final()]),
    )

    created = await authenticated_client.post(
        f"{AGENT_BASE}/runs", json={"symbol": "AAPL", "timeframe": "1h", "mode": "PROPOSE"}
    )
    assert created.status_code == 201, created.text
    run = created.json()
    assert run["status"] == "COMPLETED"
    assert run["proposal_id"] is not None

    proposal = await authenticated_client.get(f"/api/v1/proposals/{run['proposal_id']}")
    assert proposal.status_code == 200
    assert proposal.json()["proposal"]["source"] == "AGENT"
    assert proposal.json()["proposal"]["status"] == "DRAFT"
    assert proposal.json()["orders"] == []

    orders = await authenticated_client.get("/api/v1/broker/orders")
    assert orders.status_code == 200
    assert orders.json()["total"] == 0


async def test_run_listing_and_detail(authenticated_client: AsyncClient, monkeypatch) -> None:
    await _configure_provider(authenticated_client)
    monkeypatch.setattr("app.agents.service.create_provider", fake_factory(responses=[_final()]))
    created = await authenticated_client.post(
        f"{AGENT_BASE}/runs", json={"symbol": "MSFT", "timeframe": "1h"}
    )
    run_id = created.json()["id"]

    listed = await authenticated_client.get(f"{AGENT_BASE}/runs")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    detail = await authenticated_client.get(f"{AGENT_BASE}/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == run_id
