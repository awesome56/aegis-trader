"""Risk snapshot model for historical risk monitoring."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import MONEY, Base, JSONType, TimestampMixin, UUIDMixin
from app.models.enums import RiskLevel


class RiskSnapshot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "risk_snapshots"

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, native_enum=False), default=RiskLevel.SAFE, nullable=False
    )
    open_positions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trades_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exposure_pct: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    daily_pnl: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    drawdown_pct: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSONType)

    portfolio: Mapped[Portfolio] = relationship(back_populates="risk_snapshots")  # noqa: F821

    __table_args__ = (Index("ix_risk_snapshots_portfolio_time", "portfolio_id", "snapshot_time"),)
