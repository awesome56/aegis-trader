"""Encrypted broker connections (Phase 10).

Credentials are encrypted at rest and never returned to clients. This is the
same secure pattern used for LLM provider credentials.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import BrokerEnvironment, ProviderStatus


class BrokerConnection(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "broker_connections"
    __table_args__ = (
        Index("ix_broker_connections_user_env", "user_id", "environment"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    environment: Mapped[BrokerEnvironment] = mapped_column(
        Enum(BrokerEnvironment, native_enum=False), nullable=False, index=True
    )
    account_external_id: Mapped[str | None] = mapped_column(String(255))

    encrypted_api_key: Mapped[str | None] = mapped_column(Text)
    encrypted_api_secret: Mapped[str | None] = mapped_column(Text)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text)
    api_key_last_four: Mapped[str | None] = mapped_column(String(4))

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[ProviderStatus] = mapped_column(
        Enum(ProviderStatus, native_enum=False), default=ProviderStatus.UNTESTED, nullable=False
    )
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
