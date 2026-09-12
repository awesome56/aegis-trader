"""Risk REST API tests."""

from __future__ import annotations

from decimal import Decimal

from httpx import AsyncClient

CONFIRM = {"confirm": True, "reason": "test"}


async def _resume(client: AsyncClient) -> None:
    await client.post("/api/v1/risk/resume", json=CONFIRM)


async def test_requires_authentication(client: AsyncClient) -> None:
    for path in ("/api/v1/risk", "/api/v1/risk/settings", "/api/v1/risk/trading-status"):
        assert (await client.get(path)).status_code == 401


async def test_overview(authenticated_client: AsyncClient) -> None:
    await _resume(authenticated_client)
    response = await authenticated_client.get("/api/v1/risk")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"SAFE", "WARNING", "CRITICAL"}
    assert body["trading_state"] in {
        "TRADING_ENABLED",
        "TRADING_PAUSED",
        "TRADING_DISABLED",
        "EMERGENCY_STOP",
    }
    assert body["utilizations"]


async def test_settings_get_and_update(authenticated_client: AsyncClient) -> None:
    current = await authenticated_client.get("/api/v1/risk/settings")
    assert current.status_code == 200
    assert current.json()["require_stop_loss"] is True

    updated = await authenticated_client.put(
        "/api/v1/risk/settings", json={"max_position_percent": "8", "require_stop_loss": False}
    )
    assert updated.status_code == 200
    assert Decimal(updated.json()["max_position_percent"]) == Decimal("8")
    assert updated.json()["require_stop_loss"] is False

    invalid = await authenticated_client.put(
        "/api/v1/risk/settings", json={"unknown_sector_policy": "nope"}
    )
    assert invalid.status_code == 422


async def test_evaluate_and_evaluation_history(authenticated_client: AsyncClient) -> None:
    await _resume(authenticated_client)
    payload = {
        "symbol": "AAPL",
        "side": "BUY",
        "requested_quantity": "1",
        "entry_price": "100",
        "stop_loss": "95",
        "take_profit": "115",
    }
    evaluated = await authenticated_client.post("/api/v1/risk/evaluate", json=payload)
    assert evaluated.status_code == 200, evaluated.text
    assert evaluated.json()["decision"] in {
        "APPROVED",
        "APPROVED_WITH_WARNINGS",
        "REJECTED",
        "ERROR",
    }

    listing = await authenticated_client.get("/api/v1/risk/evaluations")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] >= 1
    evaluation_id = body["items"][0]["id"]

    detail = await authenticated_client.get(f"/api/v1/risk/evaluations/{evaluation_id}")
    assert detail.status_code == 200

    events = await authenticated_client.get("/api/v1/risk/events")
    assert events.status_code == 200


async def test_trading_controls_require_confirmation(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.post("/api/v1/risk/pause", json={})
    assert response.status_code == 422


async def test_pause_blocks_then_resume(authenticated_client: AsyncClient) -> None:
    paused = await authenticated_client.post("/api/v1/risk/pause", json=CONFIRM)
    assert paused.status_code == 200
    assert paused.json()["trading_state"] == "TRADING_PAUSED"

    rejected = await authenticated_client.post(
        "/api/v1/risk/evaluate",
        json={
            "symbol": "AAPL",
            "side": "BUY",
            "requested_quantity": "1",
            "entry_price": "100",
            "stop_loss": "95",
            "take_profit": "115",
        },
    )
    assert rejected.json()["decision"] == "REJECTED"
    assert "TRADING_STATE" in rejected.json()["reasons"]

    resumed = await authenticated_client.post("/api/v1/risk/resume", json=CONFIRM)
    assert resumed.json()["trading_state"] == "TRADING_ENABLED"


async def test_emergency_stop(authenticated_client: AsyncClient) -> None:
    stop = await authenticated_client.post("/api/v1/risk/emergency-stop", json=CONFIRM)
    assert stop.status_code == 200
    assert stop.json()["trading_state"] == "EMERGENCY_STOP"

    status = await authenticated_client.get("/api/v1/risk/trading-status")
    assert status.json()["trading_state"] == "EMERGENCY_STOP"

    # restore for any later tests in the session
    await authenticated_client.post("/api/v1/risk/resume", json=CONFIRM)
