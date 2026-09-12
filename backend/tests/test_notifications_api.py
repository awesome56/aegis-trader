"""Notification service and API tests."""

from __future__ import annotations

from httpx import AsyncClient

BUY = {
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": "5",
}


async def test_notifications_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/notifications")).status_code == 401
    assert (await client.get("/api/v1/notifications/unread-count")).status_code == 401


async def test_order_generates_notification_and_read_flow(
    authenticated_client: AsyncClient,
) -> None:
    initial = await authenticated_client.get("/api/v1/notifications/unread-count")
    assert initial.json()["unread"] == 0

    await authenticated_client.post(
        "/api/v1/broker/orders", json={**BUY, "idempotency_key": "notify-1"}
    )

    unread = await authenticated_client.get("/api/v1/notifications/unread-count")
    assert unread.json()["unread"] == 1

    listed = await authenticated_client.get("/api/v1/notifications")
    body = listed.json()
    assert body["total"] == 1
    notification = body["items"][0]
    assert notification["title"] == "Order filled"
    assert notification["category"] == "TRADING"
    assert notification["is_read"] is False

    marked = await authenticated_client.post(f"/api/v1/notifications/{notification['id']}/read")
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    unread_after = await authenticated_client.get("/api/v1/notifications/unread-count")
    assert unread_after.json()["unread"] == 0

    await authenticated_client.post(
        "/api/v1/broker/orders", json={**BUY, "idempotency_key": "notify-2"}
    )
    read_all = await authenticated_client.post("/api/v1/notifications/read-all")
    assert read_all.json()["unread"] == 0
    final = await authenticated_client.get("/api/v1/notifications/unread-count")
    assert final.json()["unread"] == 0


async def test_mark_unknown_notification(authenticated_client: AsyncClient) -> None:
    import uuid

    response = await authenticated_client.post(f"/api/v1/notifications/{uuid.uuid4()}/read")
    assert response.status_code == 404
