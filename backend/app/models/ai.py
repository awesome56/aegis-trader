"""AI provider configuration (encrypted credentials)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import ProviderStatus


class AIProviderConfig(UUIDMixin, TimestampMixin, Base):
    """A user's LLM provider configuration.

    The API token is stored **encrypted at rest** (Fernet) and never returned to
    clients; only the last four characters are exposed for identification.
    """

    __tablename__ = "ai_provider_configs"
    __table_args__ = (Index("ix_ai_provider_configs_user_default", "user_id", "is_default"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(255))
    encrypted_api_key: Mapped[str | None] = mapped_column(Text)
    api_key_last_four: Mapped[str | None] = mapped_column(String(4))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[ProviderStatus] = mapped_column(
        Enum(ProviderStatus, native_enum=False), default=ProviderStatus.UNTESTED, nullable=False
    )
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
