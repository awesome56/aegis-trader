"""System status / live-trading interlock tests."""

from __future__ import annotations

from httpx import AsyncClient


async def test_system_status_paper_mode(client: AsyncClient) -> None:
    response = await client.get("/api/v1/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["trading_mode"] == "paper"
    assert body["live_trading_enabled"] is False
    assert body["kill_switch_state"] == "TRADING_ENABLED"

    guard = body["live_trading_guard"]
    assert guard["allowed"] is False
    assert len(guard["missing_requirements"]) == 4
