"""Strategy REST API tests."""

from __future__ import annotations

import uuid

from httpx import AsyncClient


async def test_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/strategies")).status_code == 401
    assert (await client.get("/api/v1/strategies/signals")).status_code == 401


async def test_list_strategies(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get("/api/v1/strategies")
    assert response.status_code == 200
    body = response.json()
    keys = {item["key"] for item in body}
    assert keys == {"trend_following", "momentum", "mean_reversion"}
    for item in body:
        assert item["signal_count"] == 0
        assert item["last_signal_at"] is None


async def test_enable_and_disable(authenticated_client: AsyncClient) -> None:
    strategies = (await authenticated_client.get("/api/v1/strategies")).json()
    trend = next(item for item in strategies if item["key"] == "trend_following")

    enabled = await authenticated_client.post(f"/api/v1/strategies/{trend['id']}/enable")
    assert enabled.status_code == 200
    assert enabled.json()["is_enabled"] is True

    disabled = await authenticated_client.post(f"/api/v1/strategies/{trend['id']}/disable")
    assert disabled.json()["is_enabled"] is False


async def test_detail_and_unknown(authenticated_client: AsyncClient) -> None:
    strategies = (await authenticated_client.get("/api/v1/strategies")).json()
    trend = next(item for item in strategies if item["key"] == "trend_following")
    detail = await authenticated_client.get(f"/api/v1/strategies/{trend['id']}")
    assert detail.status_code == 200
    assert "recent_signals" in detail.json()

    missing = await authenticated_client.get(f"/api/v1/strategies/{uuid.uuid4()}")
    assert missing.status_code == 404


async def test_evaluate_then_signals(authenticated_client: AsyncClient) -> None:
    strategies = (await authenticated_client.get("/api/v1/strategies")).json()
    for item in strategies:
        await authenticated_client.post(f"/api/v1/strategies/{item['id']}/enable")

    evaluation = await authenticated_client.post(
        "/api/v1/strategies/evaluate", json={"symbol": "AAPL", "timeframe": "1h"}
    )
    assert evaluation.status_code == 200, evaluation.text
    assert len(evaluation.json()) == 3

    signals = await authenticated_client.get("/api/v1/strategies/signals")
    assert signals.status_code == 200
    assert set(signals.json()) >= {"items", "total", "page", "page_size"}

    filtered = await authenticated_client.get(
        "/api/v1/strategies/signals", params={"direction": "LONG", "symbol": "AAPL"}
    )
    assert filtered.status_code == 200

    by_strategy = await authenticated_client.get(
        f"/api/v1/strategies/{strategies[0]['id']}/signals"
    )
    assert by_strategy.status_code == 200


async def test_evaluate_specific_ids(authenticated_client: AsyncClient) -> None:
    strategies = (await authenticated_client.get("/api/v1/strategies")).json()
    trend = next(item for item in strategies if item["key"] == "trend_following")
    await authenticated_client.post(f"/api/v1/strategies/{trend['id']}/enable")
    response = await authenticated_client.post(
        "/api/v1/strategies/evaluate",
        json={"symbol": "AAPL", "timeframe": "1h", "strategy_ids": [trend["id"]]},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["strategy_key"] == "trend_following"
