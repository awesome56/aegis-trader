"""System event (audit) and notification models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, UUIDMixin
from app.models.enums import NotificationSeverity, TradingState


class SystemEvent(UUIDMixin, TimestampMixin, Base):
    """Append-only audit record. Never silently discard failures."""

    __tablename__ = "system_events"

    event_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(NotificationSeverity, native_enum=False),
        default=NotificationSeverity.INFO,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    actor: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[dict | None] = mapped_column(JSONType)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    __table_args__ = (Index("ix_system_events_type_occurred", "event_type", "occurred_at"),)


class Notification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(NotificationSeverity, native_enum=False),
        default=NotificationSeverity.INFO,
        nullable=False,
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict | None] = mapped_column(JSONType)

    user: Mapped[User] = relationship(back_populates="notifications")  # noqa: F821

    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read"),)


class SystemState(UUIDMixin, TimestampMixin, Base):
    """Persisted system-wide trading state (kill switch).

    Stored in the database, not process memory, so an EMERGENCY_STOP survives a
    restart. The row is keyed for future extension (e.g. per-scope switches).
    """

    __tablename__ = "system_state"

    key: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, default="trading"
    )
    trading_state: Mapped[TradingState] = mapped_column(
        Enum(TradingState, native_enum=False),
        default=TradingState.TRADING_ENABLED,
        nullable=False,
        index=True,
    )
    previous_state: Mapped[TradingState | None] = mapped_column(
        Enum(TradingState, native_enum=False)
    )
    reason: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str | None] = mapped_column(String(128))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
