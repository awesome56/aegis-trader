"""Notification and system-event repositories."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models.enums import NotificationSeverity
from app.models.system import Notification, SystemEvent
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_user(self, user_id: uuid.UUID, *, unread_only: bool = False) -> int:
        stmt = select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        return int(await self.session.scalar(stmt) or 0)

    async def unread_count(self, user_id: uuid.UUID) -> int:
        return await self.count_for_user(user_id, unread_only=True)

    async def get_for_user(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification | None:
        stmt = select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        notifications = await self.list_for_user(user_id, unread_only=True, limit=10_000)
        now = datetime.now(UTC)
        for notification in notifications:
            notification.is_read = True
            notification.read_at = now
        await self.session.flush()
        return len(notifications)


class SystemEventRepository(BaseRepository[SystemEvent]):
    model = SystemEvent

    async def record(
        self,
        *,
        event_type: str,
        source: str,
        message: str,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        correlation_id: str | None = None,
        actor: str | None = None,
        payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> SystemEvent:
        event = SystemEvent(
            event_type=event_type,
            source=source,
            message=message,
            severity=severity,
            correlation_id=correlation_id,
            actor=actor,
            payload=payload,
            occurred_at=occurred_at or datetime.now(UTC),
        )
        return await self.add(event)

    async def list_events(
        self,
        *,
        event_type_prefix: str | None = None,
        severity: NotificationSeverity | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SystemEvent]:
        stmt = select(SystemEvent)
        if event_type_prefix is not None:
            stmt = stmt.where(SystemEvent.event_type.like(f"{event_type_prefix}%"))
        if severity is not None:
            stmt = stmt.where(SystemEvent.severity == severity)
        stmt = stmt.order_by(SystemEvent.occurred_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_events(
        self, *, event_type_prefix: str | None = None, severity: NotificationSeverity | None = None
    ) -> int:
        stmt = select(func.count()).select_from(SystemEvent)
        if event_type_prefix is not None:
            stmt = stmt.where(SystemEvent.event_type.like(f"{event_type_prefix}%"))
        if severity is not None:
            stmt = stmt.where(SystemEvent.severity == severity)
        return int(await self.session.scalar(stmt) or 0)
