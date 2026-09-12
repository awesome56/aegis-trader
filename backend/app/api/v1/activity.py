"""Activity timeline API (authenticated)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import CurrentUser, DbSession, get_current_user
from app.models.enums import NotificationSeverity
from app.repositories.notification import SystemEventRepository
from app.schemas.activity import ActivityEventSchema, ActivityPageSchema

router = APIRouter(tags=["activity"], dependencies=[Depends(get_current_user)])


@router.get("/activity", response_model=ActivityPageSchema, summary="Audit activity timeline")
async def list_activity(
    session: DbSession,
    user: CurrentUser,
    source: Annotated[str | None, Query(description="Filter by component/source")] = None,
    severity: Annotated[NotificationSeverity | None, Query()] = None,
    event_type: Annotated[str | None, Query(description="Event type prefix filter")] = None,
    start: Annotated[datetime | None, Query(description="ISO 8601 start")] = None,
    end: Annotated[datetime | None, Query(description="ISO 8601 end")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ActivityPageSchema:
    _ = user
    repo = SystemEventRepository(session)
    events = await repo.list_events(
        event_type_prefix=event_type,
        severity=severity,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    if source is not None:
        events = [event for event in events if event.source == source]
    if start is not None:
        events = [event for event in events if event.occurred_at >= start]
    if end is not None:
        events = [event for event in events if event.occurred_at <= end]
    total = await repo.count_events(event_type_prefix=event_type, severity=severity)
    return ActivityPageSchema(
        items=[ActivityEventSchema.model_validate(event) for event in events],
        total=total,
        page=page,
        page_size=page_size,
    )
