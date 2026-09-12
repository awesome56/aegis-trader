"""Event publisher abstraction.

The default publisher delivers in-process. The abstraction exists so a
Redis Pub/Sub implementation can be dropped in for multi-worker deployments
without touching domain services. See the completion notes for this limitation.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.core.logging import get_logger
from app.realtime.bus import ConnectionManager
from app.realtime.events import DomainEvent

logger = get_logger(__name__)


class EventPublisher(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...


class InProcessEventPublisher:
    def __init__(self, manager: ConnectionManager) -> None:
        self._manager = manager

    async def publish(self, event: DomainEvent) -> None:
        payload = event.envelope()
        if event.user_id is not None:
            await self._manager.send_to_user(event.user_id, payload)
        else:
            await self._manager.broadcast(payload)


_manager = ConnectionManager()
_publisher: EventPublisher = InProcessEventPublisher(_manager)


def get_connection_manager() -> ConnectionManager:
    return _manager


def get_event_publisher() -> EventPublisher:
    return _publisher


def set_event_publisher(publisher: EventPublisher) -> None:
    """Swap the publisher (used by tests and future process-wide brokers)."""
    global _publisher
    _publisher = publisher


async def publish_pending(session_info: dict[str, Any]) -> int:
    """Publish and clear any events queued on a session. Best-effort."""
    events: list[DomainEvent] = session_info.pop("pending_events", [])
    publisher = get_event_publisher()
    for event in events:
        try:
            await publisher.publish(event)
        except Exception as exc:  # noqa: BLE001 - never break the request
            logger.warning("event_publish_failed", domain_event=event.event, error=str(exc))
    return len(events)
