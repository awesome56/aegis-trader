"""Portfolio and portfolio snapshot models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY, Base, JSONType, TimestampMixin, UUIDMixin


class Portfolio(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "portfolios"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    broker_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    cash: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="portfolios")  # noqa: F821
    broker_account: Mapped[BrokerAccount | None] = relationship(  # noqa: F821
        back_populates="portfolios"
    )
    positions: Mapped[list[Position]] = relationship(  # noqa: F821
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    orders: Mapped[list[Order]] = relationship(  # noqa: F821
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    trades: Mapped[list[Trade]] = relationship(  # noqa: F821
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list[PortfolioSnapshot]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    risk_snapshots: Mapped[list[RiskSnapshot]] = relationship(  # noqa: F821
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class PortfolioSnapshot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "portfolio_snapshots"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    cash: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    equity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    buying_power: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    invested: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    daily_pnl: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    total_return_pct: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    daily_return_pct: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    exposure_pct: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    positions: Mapped[list | None] = mapped_column(JSONType)

    portfolio: Mapped[Portfolio] = relationship(back_populates="snapshots")

    __table_args__ = (
        Index("ix_portfolio_snapshots_portfolio_time", "portfolio_id", "snapshot_time"),
    )
