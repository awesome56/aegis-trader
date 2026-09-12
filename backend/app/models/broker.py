"""Broker account model."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY, Base, TimestampMixin, UUIDMixin
from app.models.enums import BrokerMode


class BrokerAccount(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "broker_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    broker: Mapped[str] = mapped_column(String(64), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[BrokerMode] = mapped_column(
        Enum(BrokerMode, native_enum=False), default=BrokerMode.PAPER, nullable=False
    )
    external_account_id: Mapped[str | None] = mapped_column(String(255), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Only ever persist *references* to secrets held in the secret store, never
    # raw credentials in the application database.
    credentials_ref: Mapped[str | None] = mapped_column(String(255))
    cash_balance: Mapped[object] = mapped_column(MONEY, default=0, nullable=False)
    buying_power: Mapped[object] = mapped_column(MONEY, default=0, nullable=False)
    realized_pnl: Mapped[object] = mapped_column(MONEY, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="broker_accounts")  # noqa: F821
    portfolios: Mapped[list[Portfolio]] = relationship(back_populates="broker_account")  # noqa: F821
    orders: Mapped[list[Order]] = relationship(back_populates="broker_account")  # noqa: F821
