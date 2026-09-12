"""Notification REST API (authenticated, owner-scoped, paginated)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.auth.dependencies import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.notifications.service import NotificationService
from app.schemas.notifications import (
    NotificationPageSchema,
    NotificationSchema,
    UnreadCountSchema,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationPageSchema, summary="List notifications")
async def list_notifications(
    session: DbSession,
    user: CurrentUser,
    unread_only: bool = Query(default=False),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> NotificationPageSchema:
    service = NotificationService(session)
    items, total = await service.list_notifications(
        user.id, unread_only=unread_only, limit=page_size, offset=(page - 1) * page_size
    )
    return NotificationPageSchema(
        items=[NotificationSchema.from_model(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/unread-count", response_model=UnreadCountSchema, summary="Unread notification count")
async def unread_count(session: DbSession, user: CurrentUser) -> UnreadCountSchema:
    return UnreadCountSchema(unread=await NotificationService(session).unread_count(user.id))


@router.post("/{notification_id}/read", response_model=NotificationSchema, summary="Mark read")
async def mark_read(
    notification_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> NotificationSchema:
    notification = await NotificationService(session).mark_read(notification_id, user.id)
    if notification is None:
        raise NotFoundError(f"Notification {notification_id} not found")
    return NotificationSchema.from_model(notification)


@router.post("/read-all", response_model=UnreadCountSchema, summary="Mark all read")
async def mark_all_read(session: DbSession, user: CurrentUser) -> UnreadCountSchema:
    await NotificationService(session).mark_all_read(user.id)
    return UnreadCountSchema(unread=0)
