"""Notification API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NotificationSchema(_Schema):
    id: uuid.UUID
    category: str
    severity: str
    title: str
    message: str
    is_read: bool
    read_at: datetime | None
    payload: dict | None
    created_at: datetime

    @classmethod
    def from_model(cls, model) -> NotificationSchema:  # noqa: ANN001
        return cls(
            id=model.id,
            category=model.type,
            severity=model.severity.value
            if hasattr(model.severity, "value")
            else str(model.severity),
            title=model.title,
            message=model.message,
            is_read=model.is_read,
            read_at=model.read_at,
            payload=model.payload,
            created_at=model.created_at,
        )


class NotificationPageSchema(_Schema):
    items: list[NotificationSchema]
    total: int
    page: int
    page_size: int


class UnreadCountSchema(_Schema):
    unread: int
