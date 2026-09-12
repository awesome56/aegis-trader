"""Typed internal domain events.

Services append these to the current session (``session.info['pending_events']``)
and the request unit-of-work publishes them **after commit**, so a fill is never
broadcast if its transaction rolled back.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

EVENT_VERSION = 1


class DomainEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: str
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: int = EVENT_VERSION
    data: dict[str, Any] = Field(default_factory=dict)
    # Optional routing target. When set, the event is delivered only to that user.
    user_id: uuid.UUID | None = None

    def envelope(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "data": self.data,
        }


def queue_event(session_info: dict[str, Any], event: DomainEvent) -> None:
    """Append an event to a session's pending list (published post-commit)."""
    session_info.setdefault("pending_events", []).append(event)
