"""Domain event envelope and publish-after-commit tests."""

from __future__ import annotations

import uuid

from app.realtime.events import DomainEvent, queue_event
from app.realtime.publisher import get_event_publisher, publish_pending, set_event_publisher
from httpx import AsyncClient

ORDER = {
    "symbol": "AAPL",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": "4",
    "idempotency_key": "events-1",
}


class RecordingPublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)


def test_envelope_has_required_fields_and_unique_ids() -> None:
    first = DomainEvent(event="order.filled", data={"order_id": "1"})
    second = DomainEvent(event="order.filled", data={"order_id": "1"})
    assert first.event_id != second.event_id

    envelope = first.envelope()
    assert set(envelope) == {"event", "event_id", "timestamp", "version", "data"}
    assert envelope["version"] == 1
    assert envelope["event"] == "order.filled"


def test_queue_event_appends() -> None:
    info: dict = {}
    queue_event(info, DomainEvent(event="position.updated"))
    queue_event(info, DomainEvent(event="portfolio.updated"))
    assert [event.event for event in info["pending_events"]] == [
        "position.updated",
        "portfolio.updated",
    ]


async def test_publish_pending_drains_and_delivers() -> None:
    recorder = RecordingPublisher()
    original = get_event_publisher()
    set_event_publisher(recorder)
    try:
        info: dict = {}
        queue_event(info, DomainEvent(event="portfolio.updated", user_id=uuid.uuid4()))
        count = await publish_pending(info)
    finally:
        set_event_publisher(original)

    assert count == 1
    assert info.get("pending_events") in (None, [])
    assert [event.event for event in recorder.events] == ["portfolio.updated"]


async def test_broker_events_published_after_commit(authenticated_client: AsyncClient) -> None:
    recorder = RecordingPublisher()
    original = get_event_publisher()
    set_event_publisher(recorder)
    try:
        response = await authenticated_client.post("/api/v1/broker/orders", json=ORDER)
        assert response.status_code == 201, response.text
        assert response.json()["status"] == "FILLED"
    finally:
        set_event_publisher(original)

    names = [event.event for event in recorder.events]
    assert "order.created" in names
    assert "order.submitted" in names
    assert "execution.created" in names
    assert "position.created" in names
    assert "order.filled" in names
    assert "notification.created" in names
    # Every event carries a unique id for client-side dedupe.
    ids = [event.event_id for event in recorder.events]
    assert len(ids) == len(set(ids))
