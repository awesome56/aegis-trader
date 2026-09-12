"""Activity (SystemEvent) API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActivityEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    severity: str
    source: str
    message: str
    actor: str | None
    correlation_id: str | None
    payload: dict | None
    occurred_at: datetime


class ActivityPageSchema(BaseModel):
    items: list[ActivityEventSchema]
    total: int
    page: int
    page_size: int
