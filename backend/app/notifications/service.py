"""Notification service: durable user notifications + realtime delivery.

Notifications are persisted (durable audit for the user) and a
``notification.created`` event is queued for best-effort WebSocket delivery
after the surrounding transaction commits.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationSeverity
from app.models.system import Notification
from app.realtime.events import DomainEvent, queue_event
from app.repositories.notification import NotificationRepository

# Notification categories. Future phases may add RISK/AGENT/STRATEGY.
CATEGORY_TRADING = "TRADING"
CATEGORY_BROKER = "BROKER"
CATEGORY_PORTFOLIO = "PORTFOLIO"
CATEGORY_SYSTEM = "SYSTEM"
CATEGORY_MARKET = "MARKET"
CATEGORY_RISK = "RISK"


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = NotificationRepository(session)

    async def create_notification(
        self,
        *,
        user_id: uuid.UUID,
        category: str,
        title: str,
        message: str,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        payload: dict[str, Any] | None = None,
        event: str = "notification.created",
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=category,
            title=title,
            message=message,
            severity=severity,
            is_read=False,
            payload=payload,
        )
        await self._repo.add(notification)
        queue_event(
            self._session.info,
            DomainEvent(
                event=event,
                data={
                    "notification_id": str(notification.id),
                    "category": category,
                    "severity": severity.value,
                    "title": title,
                    "message": message,
                },
                user_id=user_id,
            ),
        )
        return notification

    async def list_notifications(
        self,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        items = await self._repo.list_for_user(
            user_id, unread_only=unread_only, limit=limit, offset=offset
        )
        total = await self._repo.count_for_user(user_id, unread_only=unread_only)
        return items, total

    async def unread_count(self, user_id: uuid.UUID) -> int:
        return await self._repo.unread_count(user_id)

    async def mark_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification | None:
        from datetime import UTC, datetime

        notification = await self._repo.get_for_user(notification_id, user_id)
        if notification is None:
            return None
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(UTC)
            await self._session.flush()
        return notification

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        return await self._repo.mark_all_read(user_id)
