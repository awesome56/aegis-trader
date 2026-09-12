"""Proposal REST API end-to-end (create → evaluate → execute)."""

from __future__ import annotations

from httpx import AsyncClient

BASE = "/api/v1/proposals"

LOOSE_RISK = {
    "min_strategy_confidence": "0",
    "min_reward_risk_ratio": "0.1",
    "require_stop_loss": False,
    "require_strategy_signal": False,
    "max_risk_per_trade_percent": "50",
    "unknown_sector_policy": "allow",
}


def _payload(**overrides: object) -> dict:
    data: dict = {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": "5",
        "confidence": "0.9",
    }
    data.update(overrides)
    return data


async def test_create_list_and_detail(authenticated_client: AsyncClient) -> None:
    created = await authenticated_client.post(BASE, json=_payload(idempotency_key="api-1"))
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "DRAFT"
    assert body["symbol"] == "AAPL"
    proposal_id = body["id"]

    listed = await authenticated_client.get(BASE)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    detail = await authenticated_client.get(f"{BASE}/{proposal_id}")
    assert detail.status_code == 200
    assert detail.json()["proposal"]["id"] == proposal_id
    assert detail.json()["evaluations"] == []


async def test_evaluate_then_execute(authenticated_client: AsyncClient) -> None:
    await authenticated_client.put("/api/v1/risk/settings", json=LOOSE_RISK)
    created = await authenticated_client.post(BASE, json=_payload(idempotency_key="api-2"))
    proposal_id = created.json()["id"]

    evaluated = await authenticated_client.post(f"{BASE}/{proposal_id}/evaluate")
    assert evaluated.status_code == 200, evaluated.text
    assert evaluated.json()["proposal"]["status"] == "RISK_APPROVED"

    executed = await authenticated_client.post(f"{BASE}/{proposal_id}/execute")
    assert executed.status_code == 200, executed.text
    outcome = executed.json()
    assert outcome["executed"] is True
    assert outcome["order_id"]

    detail = await authenticated_client.get(f"{BASE}/{proposal_id}")
    assert detail.json()["orders"]
    assert detail.json()["executions"]


async def test_cancel_draft(authenticated_client: AsyncClient) -> None:
    created = await authenticated_client.post(BASE, json=_payload(idempotency_key="api-3"))
    proposal_id = created.json()["id"]

    cancelled = await authenticated_client.post(f"{BASE}/{proposal_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


async def test_unknown_proposal_returns_404(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get(f"{BASE}/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
